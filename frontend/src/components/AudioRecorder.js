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

  // Enhanced monitoring
  const monitorProcessing = useCallback(async (sessionId) => {
    const maxAttempts = 120; // 2 minutes max for transcription
    let attempts = 0;

    const checkStatus = async () => {
      try {
        const statusData = await apiService.getStatus(sessionId);
        const status = statusData.status;
        const step = statusData.step || '';

        if (status === 'completed') {
          updateStatus('Transcription completed successfully!', 'success');
          setLastSessionId(sessionId);
          return;
        } else if (status === 'error') {
          updateStatus(`Processing failed: ${statusData.error}`, 'error');
          return;
        } else if (status === 'processing') {
          let stepMessage = 'Processing audio...';
          if (step === 'analyzing_audio') {
            stepMessage = 'Analyzing audio quality and format...';
          } else if (step === 'processing_audio') {
            stepMessage = 'Transcribing speech with medical optimization...';
          } else if (step === 'saving_transcript') {
            stepMessage = 'Saving transcript and extracting medical data...';
          }
          updateStatus(stepMessage, 'processing', step);
        } else if (status === 'queued') {
          updateStatus('File uploaded successfully, waiting in processing queue...', 'processing', 'queued');
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(checkStatus, 1000);
        } else {
          updateStatus('Processing timed out. Please try again or contact support.', 'error');
        }
      } catch (error) {
        console.error('Status check error:', error);
        updateStatus('Error checking processing status', 'error');
      }
    };

    checkStatus();
  }, [updateStatus]);

  // Upload audio file
  const uploadAudioFile = useCallback(async (file) => {
    try {
      updateStatus('Uploading file to medical transcription system...', 'processing');
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
      updateStatus('Upload successful! Starting medical transcription...', 'success');

      // Monitor processing status
      monitorProcessing(result.id);

    } catch (error) {
      console.error('Upload error:', error);
      updateStatus(`Upload failed: ${error.message}`, 'error');
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
      updateStatus('Requesting microphone access...', 'processing');

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
        }
      };

      // Handle recording stop
      mediaRecorderRef.current.onstop = () => {
        processRecording();
      };

      // Handle errors
      mediaRecorderRef.current.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        updateStatus('Recording error occurred', 'error');
        setIsRecording(false);
        stopTimer();
      };

      // Start recording
      mediaRecorderRef.current.start(1000);
      setIsRecording(true);

      updateStatus('Recording... Click "Stop Recording" when finished', 'processing');
      startTimer();

    } catch (error) {
      console.error('Error starting recording:', error);
      updateStatus('Could not access microphone. Please check permissions.', 'error');
    }
  }, [updateStatus, startTimer, stopTimer]);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      // Stop all tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => {
          track.stop();
        });
      }

      updateStatus('Processing recorded audio...', 'processing');
      stopTimer();
    }
  }, [isRecording, updateStatus, stopTimer]);

  // Process recording
  const processRecording = useCallback(async () => {
    try {
      if (audioChunksRef.current.length === 0) {
        updateStatus('No audio data recorded', 'error');
        return;
      }

      // Create blob from chunks
      const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

      if (audioBlob.size === 0) {
        updateStatus('Recording is empty', 'error');
        return;
      }

      if (audioBlob.size < 1000) {
        updateStatus('Recording too short. Please record at least a few seconds.', 'error');
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
      
      if (validateFile(file)) {
        updateStatus(`Selected: ${file.name} (${formatFileSize(file.size)})`, 'info');
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
    <div className="section recording-section">
      {/* Header */}
      <div className="section-header">
        <h1 className="recording-title">Medical Voice Notes</h1>
        <p className="recording-subtitle">
          AI-powered medical transcription with automated information extraction. 
          Record consultations or upload existing audio files for instant transcription and medical data analysis.
        </p>
      </div>

      {/* Action Buttons */}
      <div className="recording-actions">
        <div className="recording-primary-actions">
          {!isRecording && (
            <button onClick={startRecording} className="btn btn-primary btn-lg">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{width: '20px', height: '20px'}}>
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <path d="M12 19v4"/>
                <path d="M8 23h8"/>
              </svg>
              Start Recording
            </button>
          )}
          
          {isRecording && (
            <button onClick={stopRecording} className="btn btn-danger btn-lg">
              <svg viewBox="0 0 24 24" fill="currentColor" style={{width: '20px', height: '20px'}}>
                <rect x="6" y="6" width="12" height="12" rx="2"/>
              </svg>
              Stop Recording
            </button>
          )}
          
          <button 
            onClick={selectFileForUpload} 
            className="btn btn-secondary btn-lg"
            disabled={isRecording}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{width: '20px', height: '20px'}}>
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            Upload Audio File
          </button>
        </div>
        
        <div className="recording-secondary-actions">
          <button 
              onClick={onShowNotes}
              className="btn btn-sm btn-outline"
            >
              View Transcript
            </button>
            <button 
              onClick={onShowNotes}
              className="btn btn-sm btn-primary"
            >
              View Medical Data
            </button>
        </div>
      </div>

      {/* Timer Display */}
      {isRecording && (
        <div className="timer-display">
          {timer}
        </div>
      )}

      {/* Status Display */}
      <div className={`status-message ${status.type}`}>
        <div>{status.message}</div>
        {processingStep && (
          <div style={{fontSize: '0.875rem', marginTop: '0.5rem', opacity: 0.8}}>
            Current step: {processingStep}
          </div>
        )}
        
        {lastSessionId && status.type === 'success' && (
          <div className="flex gap-3 mt-4">
            <button 
              onClick={onShowNotes}
              className="btn btn-sm btn-outline"
            >
              View Transcript
            </button>
            <button 
              onClick={onShowSummaries}
              className="btn btn-sm btn-primary"
            >
              View Medical Data
            </button>
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {showUploadProgress && (
        <div className="upload-progress-container">
          <div className="upload-progress-header">
            <span>Uploading medical file...</span>
            <span className="upload-progress-percentage">{Math.round(uploadProgress)}%</span>
          </div>
          <div className="progress">
            <div 
              className="progress-bar" 
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

      {/* System Information */}
      

          
          
          
          
          
         
    </div>
  );
};

export default AudioRecorder;