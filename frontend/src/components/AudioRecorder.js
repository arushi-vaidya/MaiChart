import React, { useState, useRef, useCallback } from 'react';
import apiService from '../services/api';

const AudioRecorder = ({ onShowNotes }) => {
  // State management
  const [isRecording, setIsRecording] = useState(false);
  const [timer, setTimer] = useState('00:00');
  const [status, setStatus] = useState({
    message: 'Click "Start Recording" to record or "Upload Audio File" to upload an existing audio file',
    type: 'info'
  });
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showUploadProgress, setShowUploadProgress] = useState(false);
  const [lastSessionId, setLastSessionId] = useState(null);

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

  // Status update function
  const updateStatus = useCallback((message, type) => {
    setStatus({ message, type });
    
    // Auto-hide after 10 seconds for success/error messages
    if (type === 'success' || type === 'error') {
      setTimeout(() => {
        setStatus({
          message: 'Click "Start Recording" to record or "Upload Audio File" to upload an existing audio file',
          type: 'info'
        });
      }, 10000);
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

  // Monitor processing status
  const monitorProcessing = useCallback(async (sessionId) => {
    const maxAttempts = 60; // 60 seconds max for transcription
    let attempts = 0;

    const checkStatus = async () => {
      try {
        const statusData = await apiService.getStatus(sessionId);
        const status = statusData.status;
        const step = statusData.step || '';

        if (status === 'completed') {
          updateStatus('✅ Transcription completed! Text ready.', 'success');
          showTranscriptOption(sessionId);
          return;
        } else if (status === 'error') {
          updateStatus(`❌ Processing failed: ${statusData.error}`, 'error');
          return;
        } else if (status === 'processing') {
          let stepMessage = '🔄 Processing audio...';
          if (step === 'analyzing_audio') {
            stepMessage = '🔍 Analyzing audio file...';
          } else if (step === 'processing_audio') {
            stepMessage = '🎵 Transcribing audio...';
          } else if (step === 'saving_transcript') {
            stepMessage = '💾 Saving transcript...';
          }
          updateStatus(stepMessage, 'info');
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(checkStatus, 1000);
        } else {
          updateStatus('⏰ Processing timed out', 'error');
        }
      } catch (error) {
        console.error('Status check error:', error);
      }
    };

    checkStatus();
  }, [updateStatus]);

  // Show transcript option
  const showTranscriptOption = useCallback((sessionId) => {
    updateStatus(
      '✅ Transcription completed! Text ready.',
      'success'
    );
    // Store session ID for potential transcript viewing
    setLastSessionId(sessionId);
  }, [updateStatus]);

  // Show transcript
  const showTranscript = useCallback(async (sessionId) => {
    try {
      const response = await apiService.getTranscript(sessionId);
      const transcript = response.transcript;

      const transcriptText = transcript.text || 'No transcript available';
      const confidence = transcript.confidence || 0;
      const wordCount = transcript.words_count || 0;

      updateStatus(
        `📄 Transcript (${Math.round(confidence * 100)}% confidence, ${wordCount} words):\n\n"${transcriptText}"`,
        'success'
      );
    } catch (error) {
      console.error('Error loading transcript:', error);
      updateStatus('Error loading transcript', 'error');
    }
  }, [updateStatus]);

  // Upload audio file - FIXED VERSION
  const uploadAudioFile = useCallback(async (file) => {
    try {
      updateStatus('Uploading file...', 'info');
      setShowUploadProgress(true);

      // Create a proper file object for recorded blobs
      let fileToUpload = file;
      if (file instanceof Blob && !file.name) {
        // Create a proper File object from the blob
        const timestamp = Date.now();
        fileToUpload = new File([file], `recording_${timestamp}.webm`, { 
          type: 'audio/webm' 
        });
      }

      console.log('Uploading file:', {
        name: fileToUpload.name || 'unnamed',
        size: fileToUpload.size,
        type: fileToUpload.type
      });

      const result = await apiService.uploadAudio(fileToUpload, (progress) => {
        setUploadProgress(progress);
      });

      console.log('Upload successful:', result);
      setLastSessionId(result.id);
      updateStatus('Upload successful! Processing...', 'success');

      // Monitor processing status
      monitorProcessing(result.id);

    } catch (error) {
      console.error('Upload error:', error);
      updateStatus(`Upload failed: ${error.message}`, 'error');
    } finally {
      setTimeout(() => {
        setShowUploadProgress(false);
        setUploadProgress(0);
      }, 1000);
    }
  }, [updateStatus, monitorProcessing]);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      updateStatus('Requesting microphone access...', 'info');

      // Request microphone access with better audio settings
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

      // Create MediaRecorder with optimal settings
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
          console.log('Data chunk received:', event.data.size, 'bytes');
        }
      };

      // Handle recording stop
      mediaRecorderRef.current.onstop = () => {
        console.log('Recording stopped, processing...');
        processRecording();
      };

      // Handle errors
      mediaRecorderRef.current.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        updateStatus('Recording error occurred', 'error');
        setIsRecording(false);
        stopTimer();
      };

      // Start recording with regular data collection
      mediaRecorderRef.current.start(1000); // Collect data every second
      setIsRecording(true);

      updateStatus('Recording... Click "Stop Recording" when finished', 'info');
      startTimer();

      console.log('Recording started with MIME type:', mediaRecorderRef.current.mimeType);

    } catch (error) {
      console.error('Error starting recording:', error);
      updateStatus('Error: Could not access microphone', 'error');
    }
  }, [updateStatus, startTimer, stopTimer]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      console.log('Stopping recording...');
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // Stop all tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => {
          track.stop();
          console.log('Audio track stopped');
        });
      }

      updateStatus('Processing recording...', 'info');
      stopTimer();
    }
  }, [isRecording, updateStatus, stopTimer]);

  // Process recording - IMPROVED VERSION
  const processRecording = useCallback(async () => {
    try {
      console.log('Processing recording with', audioChunksRef.current.length, 'chunks');
      
      if (audioChunksRef.current.length === 0) {
        updateStatus('No audio data recorded', 'error');
        return;
      }

      // Create blob from chunks with proper MIME type
      const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

      console.log('Audio blob created:', {
        size: audioBlob.size,
        type: audioBlob.type,
        chunks: audioChunksRef.current.length
      });

      // Validate the blob
      if (audioBlob.size === 0) {
        updateStatus('Recording is empty', 'error');
        return;
      }

      // Minimum size check (should be at least a few KB for a valid recording)
      if (audioBlob.size < 1000) {
        updateStatus('Recording too short or empty', 'error');
        return;
      }

      // Upload to backend
      await uploadAudioFile(audioBlob);

    } catch (error) {
      console.error('Error processing recording:', error);
      updateStatus('Error processing recording', 'error');
    }
  }, [uploadAudioFile, updateStatus]);

  // Handle file upload
  const handleFileUpload = useCallback((event) => {
    if (event.target.files.length > 0) {
      const file = event.target.files[0];
      console.log('File selected:', {
        name: file.name,
        size: file.size,
        type: file.type
      });
      
      if (validateFile(file)) {
        updateStatus(`Selected file: ${file.name} (${formatFileSize(file.size)})`, 'info');
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

  return (
    <section className="main-section">
      <div className="title-section">
        <h1 className="main-title">Medical Voice Notes</h1>
        <p className="subtitle">Record audio or upload files for AI-powered medical transcription</p>
      </div>

      {/* Action Buttons */}
      <div className="action-buttons">
        {!isRecording && (
          <button onClick={startRecording} className="btn btn-primary">
            🎤 Start Recording
          </button>
        )}
        
        {isRecording && (
          <button onClick={stopRecording} className="btn btn-danger">
            ⏹️ Stop Recording
          </button>
        )}
        
        <button 
          onClick={selectFileForUpload} 
          className="btn btn-outline"
          disabled={isRecording}
        >
          📁 Upload Audio File
        </button>
        
        <button onClick={onShowNotes} className="btn btn-success">
          📋 View All Notes
        </button>
      </div>

      {/* Timer */}
      {isRecording && (
        <div className="timer">{timer}</div>
      )}

      {/* Status */}
      <div className={`status-indicator ${status.type}`}>
        {status.message}
        {lastSessionId && status.type === 'success' && (
          <button 
            onClick={() => showTranscript(lastSessionId)}
            className="transcript-btn"
          >
            📄 View Transcript
          </button>
        )}
      </div>

      {/* Upload Progress */}
      {showUploadProgress && (
        <div className="upload-progress">
          <div 
            className="upload-progress-bar" 
            style={{ width: `${uploadProgress}%` }}
          ></div>
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

      {/* File Format Info */}
      <div className="file-info">
        <p><strong>Supported formats:</strong> WebM, WAV, MP3, OGG, M4A</p>
        <p><strong>Maximum file size:</strong> 90MB</p>
        <p><strong>Processing:</strong> AI-powered transcription with medical term recognition</p>
        <p><strong>Output:</strong> Medical transcript with confidence scoring</p>
      </div>
    </section>
  );
};

export default AudioRecorder;