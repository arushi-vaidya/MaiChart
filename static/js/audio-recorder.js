class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.startTime = null;
        this.timer = null;
        this.lastSessionId = null;
        
        // UI Elements
        this.startBtn = document.getElementById('recordButton');
        this.stopBtn = document.getElementById('stopRecording');
        this.uploadBtn = document.getElementById('uploadRecording');
        this.saveBtn = document.getElementById('saveNote');
        this.timer = document.getElementById('timer');
        this.status = document.getElementById('status');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.uploadProgressBar = document.getElementById('uploadProgressBar');
        
        this.init();
    }
    
    init() {
        // Start Recording Button
        this.startBtn.addEventListener('click', () => {
            this.startRecording();
        });
        
        // Stop Recording Button  
        this.stopBtn.addEventListener('click', () => {
            this.stopRecording();
        });
        
        // Upload Button (placeholder for now)
        this.uploadBtn.addEventListener('click', () => {
            this.updateStatus('Upload functionality will be added later', 'info');
        });
        
        // Save Button (placeholder for now)
        this.saveBtn.addEventListener('click', () => {
            this.updateStatus('Save functionality will be added later', 'info');
        });
    }
    
    async startRecording() {
        try {
            this.updateStatus('Requesting microphone access...', 'info');
            
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 44100,
                    channelCount: 1,
                    volume: 1.0
                } 
            });
            
            // Create MediaRecorder
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm;codecs=opus'
            });
            
            this.audioChunks = [];
            
            // Handle data available
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            // Handle recording stop
            this.mediaRecorder.onstop = () => {
                this.processRecording();
            };
            
            // Start recording
            this.mediaRecorder.start(100); // Collect data every 100ms
            this.isRecording = true;
            this.startTime = Date.now();
            
            // Update UI
            this.startBtn.style.display = 'none';
            this.stopBtn.style.display = 'flex';
            this.timerDisplay.style.display = 'block';
            this.updateStatus('Recording... Click "Stop Recording" when finished', 'info');
            
            // Start timer
            this.startTimer();
            
        } catch (error) {
            console.error('Error starting recording:', error);
            this.updateStatus('Error: Could not access microphone', 'error');
        }
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            // Stop all tracks
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            
            // Update UI
            this.startBtn.style.display = 'flex';
            this.stopBtn.style.display = 'none';
            this.timerDisplay.style.display = 'none';
            this.updateStatus('Processing recording...', 'info');
            
            // Stop timer
            this.stopTimer();
        }
    }
    
    async processRecording() {
        try {
            // Create blob from chunks
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            
            console.log('Audio blob created:', {
                size: audioBlob.size,
                type: audioBlob.type
            });
            
            // Upload to backend
            await this.uploadAudio(audioBlob);
            
        } catch (error) {
            console.error('Error processing recording:', error);
            this.updateStatus('Error processing recording', 'error');
        }
    }
    
    async uploadAudio(audioBlob) {
        try {
            this.updateStatus('Uploading audio...', 'info');
            this.showUploadProgress();
            
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            formData.append('timestamp', Date.now().toString());
            
            const response = await fetch('/api/upload_audio', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Upload successful:', result);
                this.lastSessionId = result.id;
                this.updateStatus(`Upload successful! Processing...`, 'success');
                
                // Monitor processing status
                this.monitorProcessing(result.id);
            } else {
                throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
            }
            
        } catch (error) {
            console.error('Upload error:', error);
            this.updateStatus('Upload failed. Please try again.', 'error');
        } finally {
            this.hideUploadProgress();
        }
    }
    
    async monitorProcessing(sessionId) {
        const maxAttempts = 30; // 30 seconds max
        let attempts = 0;
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/status/${sessionId}`);
                if (response.ok) {
                    const statusData = await response.json();
                    const status = statusData.status;
                    
                    if (status === 'completed') {
                        this.updateStatus('✅ Processing completed! WAV file ready.', 'success');
                        this.showDownloadOption(sessionId);
                        return;
                    } else if (status === 'error') {
                        this.updateStatus(`❌ Processing failed: ${statusData.error}`, 'error');
                        return;
                    } else if (status === 'processing') {
                        this.updateStatus('🔄 Converting to WAV format...', 'info');
                    }
                }
                
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(checkStatus, 1000);
                } else {
                    this.updateStatus('⏰ Processing timed out', 'error');
                }
            } catch (error) {
                console.error('Status check error:', error);
            }
        };
        
        checkStatus();
    }
    
    showDownloadOption(sessionId) {
        // Add download link to status
        const downloadLink = document.createElement('a');
        downloadLink.href = `/api/download/${sessionId}`;
        downloadLink.download = `recording_${sessionId}.wav`;
        downloadLink.textContent = 'Download WAV File';
        downloadLink.style.display = 'block';
        downloadLink.style.marginTop = '1rem';
        downloadLink.style.color = '#3b82f6';
        downloadLink.style.textDecoration = 'none';
        downloadLink.style.fontWeight = 'bold';
        
        // Add to status element
        this.status.appendChild(downloadLink);
    }
    
    get timerDisplay() {
        return document.getElementById('timer');
    }
    
    startTimer() {
        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const minutes = Math.floor(elapsed / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            this.timerDisplay.textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }
    
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        this.timerDisplay.textContent = '00:00';
    }
    
    updateStatus(message, type) {
        this.status.textContent = message;
        this.status.className = `status-indicator ${type}`;
        
        // Auto-hide after 5 seconds for success/error messages
        if (type === 'success' || type === 'error') {
            setTimeout(() => {
                if (this.status.textContent === message) {
                    this.status.textContent = 'Click "Start Recording" to begin recording your medical notes';
                    this.status.className = 'status-indicator info';
                }
            }, 5000);
        }
    }
    
    showUploadProgress() {
        this.uploadProgress.style.display = 'block';
        // Simulate progress (you can make this real with XMLHttpRequest)
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 10;
            this.uploadProgressBar.style.width = `${progress}%`;
            if (progress >= 100) {
                clearInterval(progressInterval);
            }
        }, 100);
    }
    
    hideUploadProgress() {
        setTimeout(() => {
            this.uploadProgress.style.display = 'none';
            this.uploadProgressBar.style.width = '0%';
        }, 1000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AudioRecorder();
});