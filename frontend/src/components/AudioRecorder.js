import React, { useState, useRef, useCallback } from 'react';
import apiService from '../services/api';

const AudioRecorder = ({ onShowNotes, onShowSummaries }) => {
  // State management
  const [isRecording, setIsRecording] = useState(false);
  const [timer, setTimer] = useState('00:00');
  const [status, setStatus] = useState({
    message: 'Ready to record medical consultations or upload audio files',
    type: 'info'
  });
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showUploadProgress, setShowUploadProgress] = useState(false);
  const [lastSessionId, setLastSessionId] = useState(null);
  const [processingStep, setProcessingStep] = useState('');

  // Refs for media recording
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const startTimeRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const fileInputRef = useRef(null);

  // Timer functions
  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now();
    timerIntervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startTimeRef.current;
      const minutes = Math.floor(elapsed / 60000);
      const seconds = Math.floor((elapsed % 60000) / 1000);
      setTimer(`${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setTimer('00:00');
  }, []);

  // Enhanced status update function
  const updateStatus = useCallback((message, type, step = '') => {
    setStatus({ message, type });
    setProcessingStep(step);
    
    // Auto-hide after 15 seconds for success/error messages
    if (type === 'success' || type === 'error') {
      setTimeout(() => {
        setStatus({
          message: 'Ready to record medical consultations or upload audio files',
          type: 'info'
        });
        setProcessingStep('');
      }, 15000);
    }
  }, []);

  // File validation
  const validateFile = useCallback((file) => {
    const maxSize = 90 * 1024 * 1024; // 90MB
    const allowedTypes = ['audio/webm', 'audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/ogg', 'audio/m4a'];
    const allowedExtensions = ['.webm', '.wav', '.mp3', '.ogg', '.m4a'];

    // Check file size
    if (file.size > maxSize) {
      updateStatus('File too large. Maximum size is 90MB.', 'error');
      return false;
    }

    // For recorded blobs, we'll accept them as they should be valid WebM
    if (file instanceof Blob && file.type === 'audio/webm') {
      return true;
    }

    // Check file type and extension for uploaded files
    if (file.name) {
      const fileName = file.name.toLowerCase();
      const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
      const hasValidType = allowedTypes.includes(file.type);

      if (!hasValidExtension && !hasValidType) {
        updateStatus('Invalid file type. Please select an audio file (.webm, .wav, .mp3, .ogg, .m4a)', 'error');
        return false;
      }
    }

    return true;
  }, [updateStatus]);

  // Format file size
  const formatFileSize = useCallback((bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  // Enhanced monitoring with better step descriptions
  const monitorProcessing = useCallback(async (sessionId) => {
    const maxAttempts = 120; // 2 minutes max for transcription
    let attempts = 0;

    const checkStatus = async () => {
      try {
        const statusData = await apiService.getStatus(sessionId);
        const status = statusData.status;
        const step = statusData.step || '';

        if (status === 'completed') {
          updateStatus('✅ Medical transcription completed successfully!', 'success');
          setLastSessionId(sessionId);
          return;
        } else if (status === 'error') {
          updateStatus(`❌ Processing failed: ${statusData.error}`, 'error');
          return;
        } else if (status === 'processing') {
          let stepMessage = '🔄 Processing audio...';
          if (step === 'analyzing_audio') {
            stepMessage = '🔍 Analyzing audio quality and format...';
          } else if (step === 'processing_audio') {
            stepMessage = '🎵 Transcribing speech with medical optimization...';
          } else if (step === 'saving_transcript') {
            stepMessage = '💾 Saving transcript and extracting medical data...';
          }
          updateStatus(stepMessage, 'processing', step);
        } else if (status === 'queued') {
          updateStatus('⏳ File uploaded successfully, waiting in processing queue...', 'processing', 'queued');
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(checkStatus, 1000);
        } else {
          updateStatus('⏰ Processing timed out. Please try again or contact support.', 'error');
        }
      } catch (error) {
        console.error('Status check error:', error);
        updateStatus('❌ Error checking processing status', 'error');
      }
    };

    checkStatus();
  }, [updateStatus]);

  // Upload audio file - ENHANCED VERSION
  const uploadAudioFile = useCallback(async (file) => {
    try {
      updateStatus('📤 Uploading file to medical transcription system...', 'uploading');
      setShowUploadProgress(true);

      // Create a proper file object for recorded blobs
      let fileToUpload = file;
      if (file instanceof Blob && !file.name) {
        const timestamp = Date.now();
        fileToUpload = new File([file], `medical_recording_${timestamp}.webm`, { 
          type: 'audio/webm' 
        });
      }

      console.log('Uploading medical audio file:', {
        name: fileToUpload.name || 'unnamed',
        size: fileToUpload.size,
        type: fileToUpload.type
      });

      const result = await apiService.uploadAudio(fileToUpload, (progress) => {
        setUploadProgress(progress);
      });

      console.log('Medical audio upload successful:', result);
      setLastSessionId(result.id);
      updateStatus('✅ Upload successful! Starting medical transcription...', 'success');

      // Monitor processing status
      monitorProcessing(result.id);

    } catch (error) {
      console.error('Upload error:', error);
      updateStatus(`❌ Upload failed: ${error.message}`, 'error');
    } finally {
      setTimeout(() => {
        setShowUploadProgress(false);
        setUploadProgress(0);
      }, 2000);
    }
  }, [updateStatus, monitorProcessing]);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      updateStatus('🎙️ Requesting microphone access for medical recording...', 'info');

      // Request microphone access with enhanced audio settings
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 44100,
          channelCount: 1,
          volume: 1.0,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      streamRef.current = stream;

      // Determine the best MIME type available
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = 'audio/ogg;codecs=opus';
          if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = ''; // Let the browser choose
          }
        }
      }

      const mediaRecorderOptions = {};
      if (mimeType) {
        mediaRecorderOptions.mimeType = mimeType;
      }

      mediaRecorderRef.current = new MediaRecorder(stream, mediaRecorderOptions);
      audioChunksRef.current = [];

      // Handle data available
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
          console.log('Audio chunk recorded:', event.data.size, 'bytes');
        }
      };

      // Handle recording stop
      mediaRecorderRef.current.onstop = () => {
        console.log('Recording stopped, processing medical audio...');
        processRecording();
      };

      // Handle errors
      mediaRecorderRef.current.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        updateStatus('❌ Recording error occurred', 'error');
        setIsRecording(false);
        stopTimer();
      };

      // Start recording
      mediaRecorderRef.current.start(1000);
      setIsRecording(true);

      updateStatus('🎤 Recording medical consultation... Click "Stop Recording" when finished', 'recording');
      startTimer();

      console.log('Medical recording started with MIME type:', mediaRecorderRef.current.mimeType);

    } catch (error) {
      console.error('Error starting recording:', error);
      updateStatus('❌ Could not access microphone. Please check permissions.', 'error');
    }
  }, [updateStatus, startTimer, stopTimer]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      console.log('Stopping medical recording...');
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // Stop all tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => {
          track.stop();
          console.log('Audio track stopped');
        });
      }

      updateStatus('🔄 Processing recorded medical consultation...', 'processing');
      stopTimer();
    }
  }, [isRecording, updateStatus, stopTimer]);

  // Process recording
  const processRecording = useCallback(async () => {
    try {
      console.log('Processing medical recording with', audioChunksRef.current.length, 'chunks');
      
      if (audioChunksRef.current.length === 0) {
        updateStatus('❌ No audio data recorded', 'error');
        return;
      }

      // Create blob from chunks
      const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

      console.log('Medical audio blob created:', {
        size: audioBlob.size,
        type: audioBlob.type,
        chunks: audioChunksRef.current.length
      });

      // Validate the blob
      if (audioBlob.size === 0) {
        updateStatus('❌ Recording is empty', 'error');
        return;
      }

      if (audioBlob.size < 1000) {
        updateStatus('❌ Recording too short. Please record at least a few seconds.', 'error');
        return;
      }

      // Upload to backend
      await uploadAudioFile(audioBlob);

    } catch (error) {
      console.error('Error processing medical recording:', error);
      updateStatus('❌ Error processing recording', 'error');
    }
  }, [uploadAudioFile, updateStatus]);

  // Handle file upload
  const handleFileUpload = useCallback((event) => {
    if (event.target.files.length > 0) {
      const file = event.target.files[0];
      console.log('Medical file selected:', {
        name: file.name,
        size: file.size,
        type: file.type
      });
      
      if (validateFile(file)) {
        updateStatus(`📁 Selected: ${file.name} (${formatFileSize(file.size)})`, 'info');
        uploadAudioFile(file);
      }
    }
    // Reset file input
    event.target.value = '';
  }, [validateFile, formatFileSize, uploadAudioFile]);

  // Select file for upload
  const selectFileForUpload = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // View last transcript
  const viewLastTranscript = useCallback(async () => {
    if (!lastSessionId) return;
    
    try {
      const response = await apiService.getTranscript(lastSessionId);
      const transcript = response.transcript;
      
      // Create a note object for the modal
      const noteForModal = {
        session_id: lastSessionId,
        text: transcript.text,
        confidence: transcript.confidence,
        created_at: new Date().toISOString(),
        word_count: transcript.words_count || 0,
        duration: transcript.duration || 0
      };
      
      // You would call onOpenTranscript here if it was passed as a prop
      // For now, we'll show an alert with basic info
      const wordCount = noteForModal.word_count;
      const confidence = Math.round((noteForModal.confidence || 0) * 100);
      alert(`Medical Transcript Ready!\n\nWords: ${wordCount}\nConfidence: ${confidence}%\n\nGo to "📝 Transcripts" to view the full transcript and medical data.`);
      
    } catch (error) {
      console.error('Error loading transcript:', error);
      updateStatus('❌ Error loading transcript', 'error');
    }
  }, [lastSessionId]);

  return (
    <section className="main-section">
      {/* Enhanced Title Section */}
      <div className="title-section">
        <h1 className="main-title">🏥 Medical Voice Notes</h1>
        <p className="subtitle">
          AI-powered medical transcription with automated information extraction
        </p>
        <div className="feature-highlights">
          <div className="feature-item">
            <span className="feature-icon">🤖</span>
            <span>Medical AI Extraction</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔒</span>
            <span>HIPAA Compliant</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">⚡</span>
            <span>Real-time Processing</span>
          </div>
        </div>
      </div>

      {/* Enhanced Action Buttons */}
      <div className="recording-actions">
        <div className="primary-actions">
          {!isRecording && (
            <button onClick={startRecording} className="btn btn-primary btn-lg recording-btn">
              <span className="btn-icon">🎤</span>
              <div className="btn-text">
                <span className="btn-title">Start Recording</span>
                <span className="btn-subtitle">Begin medical consultation</span>
              </div>
            </button>
          )}
          
          {isRecording && (
            <button onClick={stopRecording} className="btn btn-danger btn-lg recording-btn active">
              <span className="btn-icon recording-pulse">⏹️</span>
              <div className="btn-text">
                <span className="btn-title">Stop Recording</span>
                <span className="btn-subtitle">End consultation</span>
              </div>
            </button>
          )}
          
          <button 
            onClick={selectFileForUpload} 
            className="btn btn-outline btn-lg upload-btn"
            disabled={isRecording}
          >
            <span className="btn-icon">📁</span>
            <div className="btn-text">
              <span className="btn-title">Upload Audio</span>
              <span className="btn-subtitle">Select existing file</span>
            </div>
          </button>
        </div>
        
        <div className="secondary-actions">
          <button onClick={onShowNotes} className="btn btn-success">
            📝 View Transcripts
          </button>
          <button onClick={onShowSummaries} className="btn btn-outline">
            🏥 Medical Summaries
          </button>
        </div>
      </div>

      {/* Enhanced Timer */}
      {isRecording && (
        <div className="recording-status">
          <div className="timer-container">
            <div className="recording-indicator">
              <div className="recording-dot"></div>
              <span>RECORDING</span>
            </div>
            <div className="timer">{timer}</div>
          </div>
          <p className="recording-tip">
            💡 Speak clearly and mention symptoms, medications, and patient details
          </p>
        </div>
      )}

      {/* Enhanced Status Display */}
      <div className="status-container">
        <div className={`status-indicator ${status.type}`}>
          <div className="status-content">
            <div className="status-message">{status.message}</div>
            {processingStep && (
              <div className="processing-step">
                Current step: {processingStep}
              </div>
            )}
          </div>
          
          {lastSessionId && (status.type === 'success' || processingStep === 'completed') && (
            <div className="success-actions">
              <button 
                onClick={viewLastTranscript}
                className="btn btn-outline btn-sm"
              >
                📄 View Transcript
              </button>
              <button 
                onClick={onShowSummaries}
                className="btn btn-primary btn-sm"
              >
                🏥 View Medical Data
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Enhanced Upload Progress */}
      {showUploadProgress && (
        <div className="upload-progress-container">
          <div className="progress-header">
            <span className="progress-label">Uploading medical file...</span>
            <span className="progress-percentage">{Math.round(uploadProgress)}%</span>
          </div>
          <div className="upload-progress">
            <div 
              className="upload-progress-bar" 
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*,.webm,.wav,.mp3,.ogg,.m4a"
        onChange={handleFileUpload}
        style={{ display: 'none' }}
      />

      {/* Enhanced File Format Info */}
      <div className="system-info">
        <div className="info-grid">
          <div className="info-card">
            <div className="info-header">
              <span className="info-icon">🎵</span>
              <span className="info-title">Supported Formats</span>
            </div>
            <div className="info-content">
              WebM, WAV, MP3, OGG, M4A
            </div>
          </div>
          
          <div className="info-card">
            <div className="info-header">
              <span className="info-icon">📏</span>
              <span className="info-title">File Size Limit</span>
            </div>
            <div className="info-content">
              Up to 90MB per file
            </div>
          </div>
          
          <div className="info-card">
            <div className="info-header">
              <span className="info-icon">🤖</span>
              <span className="info-title">AI Processing</span>
            </div>
            <div className="info-content">
              Medical transcription + data extraction
            </div>
          </div>
          
          <div className="info-card">
            <div className="info-header">
              <span className="info-icon">⚡</span>
              <span className="info-title">Processing Time</span>
            </div>
            <div className="info-content">
              ~1-2 minutes for most files
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default AudioRecorder;