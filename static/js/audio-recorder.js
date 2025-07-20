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
        
        // Create hidden file input
        this.fileInput = this.createFileInput();
        
        this.init();
    }
    
    createFileInput() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'audio/*,.webm,.wav,.mp3,.ogg,.m4a';
        input.style.display = 'none';
        document.body.appendChild(input);
        return input;
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
        
        // Upload Button
        this.uploadBtn.addEventListener('click', () => {
            this.selectFileForUpload();
        });
        
        // File input change handler
        this.fileInput.addEventListener('change', (event) => {
            if (event.target.files.length > 0) {
                this.handleFileUpload(event.target.files[0]);
            }
        });
        
        // Save Button (placeholder for now)
        this.saveBtn.addEventListener('click', () => {
            this.updateStatus('Save functionality will be added later', 'info');
        });
    }
    
    selectFileForUpload() {
        this.fileInput.click();
    }
    
    async handleFileUpload(file) {
        try {
            // Validate file
            if (!this.validateFile(file)) {
                return;
            }
            
            this.updateStatus(`Selected file: ${file.name} (${this.formatFileSize(file.size)})`, 'info');
            
            // Upload the file
            await this.uploadAudioFile(file);
            
        } catch (error) {
            console.error('File upload error:', error);
            this.updateStatus('Error uploading file. Please try again.', 'error');
        }
    }
    
    validateFile(file) {
        const maxSize = 90 * 1024 * 1024; // 90MB
        const allowedTypes = ['audio/webm', 'audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/ogg', 'audio/m4a'];
        const allowedExtensions = ['.webm', '.wav', '.mp3', '.ogg', '.m4a'];
        
        // Check file size
        if (file.size > maxSize) {
            this.updateStatus('File too large. Maximum size is 90MB.', 'error');
            return false;
        }
        
        // Check file type and extension
        const fileName = file.name.toLowerCase();
        const hasValidExtension = allowedExtensions.some(ext => fileName.endsWith(ext));
        const hasValidType = allowedTypes.includes(file.type);
        
        if (!hasValidExtension && !hasValidType) {
            this.updateStatus('Invalid file type. Please select an audio file (.webm, .wav, .mp3, .ogg, .m4a)', 'error');
            return false;
        }
        
        return true;
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async uploadAudioFile(file) {
        try {
            this.updateStatus('Uploading file...', 'info');
            this.showUploadProgress();
            
            const formData = new FormData();
            formData.append('audio', file, file.name);
            formData.append('timestamp', Date.now().toString());
            
            // Create XMLHttpRequest to track upload progress
            const xhr = new XMLHttpRequest();
            
            // Track upload progress
            xhr.upload.addEventListener('progress', (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    this.updateUploadProgress(percentComplete);
                }
            });
            
            // Handle completion
            const uploadPromise = new Promise((resolve, reject) => {
                xhr.addEventListener('load', () => {
                    if (xhr.status === 200) {
                        try {
                            const result = JSON.parse(xhr.responseText);
                            resolve(result);
                        } catch (e) {
                            reject(new Error('Invalid response format'));
                        }
                    } else {
                        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
                    }
                });
                
                xhr.addEventListener('error', () => {
                    reject(new Error('Upload failed due to network error'));
                });
                
                xhr.addEventListener('timeout', () => {
                    reject(new Error('Upload timed out'));
                });
            });
            
            // Start upload
            xhr.open('POST', '/api/upload_audio');
            xhr.timeout = 300000; // 5 minutes timeout
            xhr.send(formData);
            
            // Wait for completion
            const result = await uploadPromise;
            
            console.log('Upload successful:', result);
            this.lastSessionId = result.id;
            this.updateStatus(`Upload successful! Processing...`, 'success');
            
            // Monitor processing status
            this.monitorProcessing(result.id);
            
        } catch (error) {
            console.error('Upload error:', error);
            this.updateStatus('Upload failed. Please try again.', 'error');
        } finally {
            this.hideUploadProgress();
        }
    }
    
    updateUploadProgress(percent) {
        this.uploadProgressBar.style.width = `${percent}%`;
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
            this.uploadBtn.disabled = true; // Disable upload while recording
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
            this.uploadBtn.disabled = false; // Re-enable upload
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
        const maxAttempts = 60; // 60 seconds max for transcription
        let attempts = 0;
        
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/status/${sessionId}`);
                if (response.ok) {
                    const statusData = await response.json();
                    const status = statusData.status;
                    const step = statusData.step || '';
                    
                    if (status === 'completed') {
                        this.updateStatus('✅ Transcription completed! Text ready.', 'success');
                        this.showTranscriptOption(sessionId);
                        return;
                    } else if (status === 'error') {
                        this.updateStatus(`❌ Processing failed: ${statusData.error}`, 'error');
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
                        this.updateStatus(stepMessage, 'info');
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
    
    showTranscriptOption(sessionId) {
        // Add view transcript button to status
        const transcriptBtn = document.createElement('button');
        transcriptBtn.textContent = '📄 View Transcript';
        transcriptBtn.style.display = 'block';
        transcriptBtn.style.marginTop = '1rem';
        transcriptBtn.style.color = '#3b82f6';
        transcriptBtn.style.backgroundColor = 'transparent';
        transcriptBtn.style.border = '2px solid #3b82f6';
        transcriptBtn.style.borderRadius = '8px';
        transcriptBtn.style.padding = '0.5rem 1rem';
        transcriptBtn.style.fontWeight = 'bold';
        transcriptBtn.style.cursor = 'pointer';
        transcriptBtn.style.transition = 'all 0.2s';
        
        transcriptBtn.addEventListener('mouseover', () => {
            transcriptBtn.style.backgroundColor = '#3b82f6';
            transcriptBtn.style.color = 'white';
        });
        
        transcriptBtn.addEventListener('mouseout', () => {
            transcriptBtn.style.backgroundColor = 'transparent';
            transcriptBtn.style.color = '#3b82f6';
        });
        
        transcriptBtn.addEventListener('click', () => {
            this.showTranscript(sessionId);
        });
        
        // Clear any existing buttons
        const existingBtns = this.status.querySelectorAll('button');
        existingBtns.forEach(btn => btn.remove());
        
        // Add to status element
        this.status.appendChild(transcriptBtn);
    }
    
    async showTranscript(sessionId) {
        try {
            const response = await fetch(`/api/transcript/${sessionId}`);
            if (response.ok) {
                const data = await response.json();
                const transcript = data.transcript;
                
                // Create modal or update status with transcript
                const transcriptText = transcript.text || 'No transcript available';
                const confidence = transcript.confidence || 0;
                const wordCount = transcript.word_count || 0;
                
                this.updateStatus(
                    `📄 Transcript (${Math.round(confidence * 100)}% confidence, ${wordCount} words):\n\n"${transcriptText}"`,
                    'success'
                );
            } else {
                this.updateStatus('Error loading transcript', 'error');
            }
        } catch (error) {
            console.error('Error loading transcript:', error);
            this.updateStatus('Error loading transcript', 'error');
        }
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
        // Clear any existing buttons when updating status
        const existingBtns = this.status.querySelectorAll('button');
        existingBtns.forEach(btn => btn.remove());
        
        this.status.textContent = message;
        this.status.className = `status-indicator ${type}`;
        
        // Auto-hide after 10 seconds for success/error messages (longer for transcript)
        if (type === 'success' || type === 'error') {
            setTimeout(() => {
                if (this.status.textContent === message) {
                    this.status.textContent = 'Click "Start Recording" to record or "Upload Audio File" to upload an existing audio file';
                    this.status.className = 'status-indicator info';
                }
            }, 10000);
        }
    }
    
    showUploadProgress() {
        this.uploadProgress.style.display = 'block';
        this.uploadProgressBar.style.width = '0%';
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

let currentNotes = [];
let currentFilter = 'all';

// Navigation between sections
function showNotesSection() {
    document.getElementById('recording-section').style.display = 'none';
    document.getElementById('notes-section').style.display = 'block';

    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector('a[href="#notes"]').classList.add('active');

    loadNotes();
}

function showRecordingSection() {
    document.getElementById('notes-section').style.display = 'none';
    document.getElementById('recording-section').style.display = 'block';

    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    document.querySelector('a[href="#recording"]').classList.add('active');
}

// Load notes from backend
async function loadNotes() {
    try {
        const response = await fetch('/api/notes');
        if (response.ok) {
            const data = await response.json();
            currentNotes = data.notes || [];
            displayNotes(currentNotes);
        } else {
            console.error('Failed to load notes');
            showEmptyState();
        }
    } catch (error) {
        console.error('Error loading notes:', error);
        showEmptyState();
    }
}

// Display notes in the grid
function displayNotes(notes) {
    const notesGrid = document.getElementById('notesGrid');
    const emptyState = document.getElementById('emptyState');

    if (!notes || notes.length === 0) {
        showEmptyState();
        return;
    }

    emptyState.style.display = 'none';
    notesGrid.style.display = 'grid';

    notesGrid.innerHTML = notes.map(note => createNoteCard(note)).join('');
}

// Create a note card HTML
function createNoteCard(note) {
    const date = new Date(note.created_at || note.timestamp);
    const confidence = note.confidence || 0;
    const confidenceClass = confidence >= 0.8 ? 'confidence-high' :
        confidence >= 0.6 ? 'confidence-medium' : 'confidence-low';

    const preview = note.text ? note.text.substring(0, 200) : 'No transcript available';
    const wordCount = note.text ? note.text.split(' ').length : 0;

    return `
        <div class="note-card" onclick="openNoteModal('${note.session_id}')">
            <div class="note-header">
                <div class="note-metadata">
                    <div class="note-date">${formatDate(date)}</div>
                    <div class="note-session">ID: ${note.session_id.substring(0, 8)}...</div>
                </div>
                <div class="note-actions">
                    <button class="action-btn" onclick="event.stopPropagation(); downloadNote('${note.session_id}')" title="Download">💾</button>
                    <button class="action-btn delete" onclick="event.stopPropagation(); deleteNote('${note.session_id}')" title="Delete">🗑️</button>
                </div>
            </div>
            
            <div class="note-stats">
                <div class="stat-item">
                    <span>🎯</span>
                    <span class="${confidenceClass}">${Math.round(confidence * 100)}%</span>
                </div>
                <div class="stat-item">
                    <span>📝</span>
                    <span>${wordCount} words</span>
                </div>
                ${note.duration ? `
                <div class="stat-item">
                    <span>⏱️</span>
                    <span>${Math.round(note.duration)}s</span>
                </div>
                ` : ''}
            </div>
            
            <div class="note-text" id="text-${note.session_id}">
                ${preview}${note.text && note.text.length > 200 ? '...' : ''}
            </div>
            
            ${note.text && note.text.length > 200 ? `
            <div class="expand-btn" onclick="event.stopPropagation(); toggleExpand('${note.session_id}')">
                Click to read full transcript
            </div>
            ` : ''}
        </div>
    `;
}

// Open note in modal
function openNoteModal(sessionId) {
    const note = currentNotes.find(n => n.session_id === sessionId);
    if (!note) return;

    document.getElementById('modalTitle').textContent = `Medical Note - ${formatDate(new Date(note.created_at || note.timestamp))}`;
    document.getElementById('modalTranscript').textContent = note.text || 'No transcript available';
    document.getElementById('transcriptModal').style.display = 'block';
}

// Close modal
function closeModal() {
    document.getElementById('transcriptModal').style.display = 'none';
}

// Format date for display
function formatDate(date) {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Search functionality
document.getElementById('searchBox').addEventListener('input', function(e) {
    const searchTerm = e.target.value.toLowerCase();
    const filteredNotes = currentNotes.filter(note =>
        (note.text && note.text.toLowerCase().includes(searchTerm)) ||
        note.session_id.toLowerCase().includes(searchTerm)
    );
    displayNotes(filteredNotes);
});

// Filter functionality
document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', function() {
        document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        this.classList.add('active');

        const filter = this.dataset.filter;
        currentFilter = filter;

        let filteredNotes = [...currentNotes];
        const now = new Date();

        switch (filter) {
            case 'today':
                filteredNotes = filteredNotes.filter(note => {
                    const noteDate = new Date(note.created_at || note.timestamp);
                    return noteDate.toDateString() === now.toDateString();
                });
                break;
            case 'week':
                const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                filteredNotes = filteredNotes.filter(note => {
                    const noteDate = new Date(note.created_at || note.timestamp);
                    return noteDate >= weekAgo;
                });
                break;
            case 'high-confidence':
                filteredNotes = filteredNotes.filter(note =>
                    (note.confidence || 0) >= 0.8
                );
                break;
        }

        displayNotes(filteredNotes);
    });
});

// Refresh notes
function refreshNotes() {
    loadNotes();
}

// Download note
async function downloadNote(sessionId) {
    try {
        const response = await fetch(`/api/transcript/${sessionId}/download`);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `medical_note_${sessionId.substring(0, 8)}.txt`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }
    } catch (error) {
        console.error('Error downloading note:', error);
    }
}

// Delete note
async function deleteNote(sessionId) {
    if (!confirm('Are you sure you want to delete this medical note?')) {
        return;
    }

    try {
        const response = await fetch(`/api/cleanup/${sessionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Remove from current notes array
            currentNotes = currentNotes.filter(note => note.session_id !== sessionId);
            displayNotes(currentNotes);
        } else {
            alert('Failed to delete note');
        }
    } catch (error) {
        console.error('Error deleting note:', error);
        alert('Error deleting note');
    }
}

// Show empty state
function showEmptyState() {
    document.getElementById('notesGrid').style.display = 'none';
    document.getElementById('emptyState').style.display = 'block';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('transcriptModal');
    if (event.target === modal) {
        closeModal();
    }
}

// Navigation link handlers
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const href = this.getAttribute('href');
        if (href === '#recording') {
            showRecordingSection();
        } else if (href === '#notes') {
            showNotesSection();
        }
    });
});

// Initialize the interface
document.addEventListener('DOMContentLoaded', function() {
    // Start with recording section
    showRecordingSection();
});
