// frontend/src/components/StreamingRecorder.js
import React, { useState, useRef, useCallback } from 'react';

class StreamingAudioRecorder {
  constructor(onChunkSent, onError, onStatusUpdate) {
    this.mediaRecorder = null;
    this.audioStream = null;
    this.sessionId = null;
    this.chunkSequence = 0;
    this.isRecording = false;
    this.chunkInterval = null;
    this.recordedChunks = [];
    
    // Callbacks
    this.onChunkSent = onChunkSent;
    this.onError = onError;
    this.onStatusUpdate = onStatusUpdate;
  }

  generateSessionId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  async startRecording() {
    try {
      // Get microphone access
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });

      // Generate session ID
      this.sessionId = this.generateSessionId();
      
      // Initialize session on backend
      await this.initializeSession();

      // Setup MediaRecorder
      const options = {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 128000
      };

      this.mediaRecorder = new MediaRecorder(this.audioStream, options);
      this.chunkSequence = 0;
      this.recordedChunks = [];

      // Handle data available
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.recordedChunks.push(event.data);
        }
      };

      // Handle recording stop
      this.mediaRecorder.onstop = () => {
        this.sendFinalChunk();
      };

      // Start recording with 5-second intervals
      this.mediaRecorder.start(5000);
      this.isRecording = true;

      // Set up interval to send chunks
      this.chunkInterval = setInterval(() => {
        this.sendAccumulatedChunk();
      }, 5000);

      this.onStatusUpdate('Recording started', this.sessionId);

    } catch (error) {
      this.onError('Failed to start recording: ' + error.message);
    }
  }

  async initializeSession() {
    try {
      const response = await fetch('/api/initialize_streaming_session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: this.sessionId
        })
      });

      if (!response.ok) {
        throw new Error('Failed to initialize session');
      }
    } catch (error) {
      throw new Error('Session initialization failed: ' + error.message);
    }
  }

  async sendAccumulatedChunk() {
    if (this.recordedChunks.length === 0) return;

    // Create blob from accumulated chunks
    const chunkBlob = new Blob(this.recordedChunks, { type: 'audio/webm' });
    this.recordedChunks = []; // Clear for next chunk

    await this.sendChunk(chunkBlob, false);
  }

  async sendFinalChunk() {
    if (this.recordedChunks.length > 0) {
      const finalBlob = new Blob(this.recordedChunks, { type: 'audio/webm' });
      await this.sendChunk(finalBlob, true);
    }
  }

  async sendChunk(blob, isLastChunk = false) {
    try {
      const formData = new FormData();
      formData.append('audio', blob, `chunk_${this.chunkSequence}.webm`);
      formData.append('session_id', this.sessionId);
      formData.append('chunk_sequence', this.chunkSequence.toString());
      formData.append('is_streaming', 'true');
      formData.append('is_last_chunk', isLastChunk.toString());

      const response = await fetch('/api/upload_audio', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        this.onChunkSent(this.chunkSequence, blob.size, isLastChunk);
        this.chunkSequence++;

        if (isLastChunk) {
          this.onStatusUpdate('Recording completed and uploaded', this.sessionId);
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

    } catch (error) {
      this.onError(`Failed to send chunk ${this.chunkSequence}: ${error.message}`);
    }
  }

  stopRecording() {
    if (!this.isRecording) return;

    this.isRecording = false;

    // Clear interval
    if (this.chunkInterval) {
      clearInterval(this.chunkInterval);
      this.chunkInterval = null;
    }

    // Stop MediaRecorder
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    // Stop audio stream
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(track => track.stop());
      this.audioStream = null;
    }
  }

  getSessionId() {
    return this.sessionId;
  }

  isCurrentlyRecording() {
    return this.isRecording;
  }
}

// React Component
const StreamingRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState('Ready to record');
  const [chunksSent, setChunksSent] = useState(0);
  const [totalSize, setTotalSize] = useState(0);
  const recorderRef = useRef(null);

  const handleChunkSent = useCallback((chunkIndex, size, isLast) => {
    setChunksSent(prev => prev + 1);
    setTotalSize(prev => prev + size);
    
    if (isLast) {
      setStatus(`Recording completed. ${chunkIndex + 1} chunks sent.`);
      setIsRecording(false);
    } else {
      setStatus(`Recording... Chunk ${chunkIndex + 1} sent (${Math.round(size/1024)}KB)`);
    }
  }, []);

  const handleError = useCallback((error) => {
    setStatus(`Error: ${error}`);
    setIsRecording(false);
  }, []);

  const handleStatusUpdate = useCallback((statusMessage, sessionId) => {
    setStatus(statusMessage);
    if (sessionId) {
      setSessionId(sessionId);
    }
  }, []);

  const startRecording = async () => {
    if (!recorderRef.current) {
      recorderRef.current = new StreamingAudioRecorder(
        handleChunkSent,
        handleError,
        handleStatusUpdate
      );
    }

    try {
      await recorderRef.current.startRecording();
      setIsRecording(true);
      setChunksSent(0);
      setTotalSize(0);
    } catch (error) {
      handleError(error.message);
    }
  };

  const stopRecording = () => {
    if (recorderRef.current) {
      recorderRef.current.stopRecording();
    }
  };

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="streaming-recorder">
      <h3>Streaming Voice Recorder</h3>
      
      <div className="recorder-controls">
        <button 
          onClick={startRecording} 
          disabled={isRecording}
          className="start-btn"
        >
          {isRecording ? 'Recording...' : 'Start Recording'}
        </button>
        
        <button 
          onClick={stopRecording} 
          disabled={!isRecording}
          className="stop-btn"
        >
          Stop Recording
        </button>
      </div>

      <div className="recorder-status">
        <p><strong>Status:</strong> {status}</p>
        {sessionId && <p><strong>Session ID:</strong> {sessionId}</p>}
        {chunksSent > 0 && (
          <div>
            <p><strong>Chunks sent:</strong> {chunksSent}</p>
            <p><strong>Total size:</strong> {formatSize(totalSize)}</p>
          </div>
        )}
      </div>

      {sessionId && (
        <div className="session-link">
          <a href={`/status/${sessionId}`} target="_blank" rel="noopener noreferrer">
            View Processing Status
          </a>
        </div>
      )}

      <style jsx>{`
        .streaming-recorder {
          max-width: 500px;
          margin: 20px auto;
          padding: 20px;
          border: 1px solid #ddd;
          border-radius: 8px;
          background: #f9f9f9;
        }
        
        .recorder-controls {
          display: flex;
          gap: 10px;
          margin: 20px 0;
        }
        
        .start-btn, .stop-btn {
          padding: 12px 24px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 16px;
        }
        
        .start-btn {
          background: #4CAF50;
          color: white;
        }
        
        .start-btn:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
        
        .stop-btn {
          background: #f44336;
          color: white;
        }
        
        .stop-btn:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
        
        .recorder-status {
          background: white;
          padding: 15px;
          border-radius: 4px;
          margin: 15px 0;
        }
        
        .session-link {
          margin-top: 15px;
        }
        
        .session-link a {
          color: #2196F3;
          text-decoration: none;
        }
        
        .session-link a:hover {
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
};

export default StreamingRecorder;   