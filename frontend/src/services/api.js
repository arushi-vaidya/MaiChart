// API base URL - using proxy in package.json for development
const API_BASE_URL = '/api';

// API service class to handle all backend communication
class ApiService {
  // Upload audio file for transcription
  async uploadAudio(file, onProgress = null) {
    const formData = new FormData();
    formData.append('audio', file, file.name);
    formData.append('timestamp', Date.now().toString());

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      // Track upload progress
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            onProgress(percentComplete);
          }
        });
      }

      // Handle completion
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

      // Start upload
      xhr.open('POST', `${API_BASE_URL}/upload_audio`);
      xhr.timeout = 300000; // 5 minutes timeout
      xhr.send(formData);
    });
  }

  // Get processing status for a session
  async getStatus(sessionId) {
    const response = await fetch(`${API_BASE_URL}/status/${sessionId}`);
    if (!response.ok) {
      throw new Error(`Status check failed: ${response.status}`);
    }
    return response.json();
  }

  // Get transcript for a session
  async getTranscript(sessionId) {
    const response = await fetch(`${API_BASE_URL}/transcript/${sessionId}`);
    if (!response.ok) {
      throw new Error(`Transcript retrieval failed: ${response.status}`);
    }
    return response.json();
  }

  // Download transcript as file
  async downloadTranscript(sessionId) {
    const response = await fetch(`${API_BASE_URL}/transcript/${sessionId}/download`);
    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`);
    }
    
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

  // Get all notes
  async getAllNotes() {
    const response = await fetch(`${API_BASE_URL}/notes`);
    if (!response.ok) {
      throw new Error(`Failed to fetch notes: ${response.status}`);
    }
    return response.json();
  }

  // Search notes
  async searchNotes(query) {
    const response = await fetch(`${API_BASE_URL}/notes/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) {
      throw new Error(`Search failed: ${response.status}`);
    }
    return response.json();
  }

  // Get notes statistics
  async getNotesStats() {
    const response = await fetch(`${API_BASE_URL}/notes/stats`);
    if (!response.ok) {
      throw new Error(`Stats retrieval failed: ${response.status}`);
    }
    return response.json();
  }

  // Delete a session
  async deleteSession(sessionId) {
    const response = await fetch(`${API_BASE_URL}/cleanup/${sessionId}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      throw new Error(`Delete failed: ${response.status}`);
    }
    return response.json();
  }

  // Export all notes
  async exportNotes() {
    const response = await fetch(`${API_BASE_URL}/export/notes`);
    if (!response.ok) {
      throw new Error(`Export failed: ${response.status}`);
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `medical_notes_export_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  // Health check
  async healthCheck() {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return response.json();
  }

  // Get system stats
  async getSystemStats() {
    const response = await fetch(`${API_BASE_URL}/stats`);
    if (!response.ok) {
      throw new Error(`Stats failed: ${response.status}`);
    }
    return response.json();
  }
}

// Export singleton instance
export default new ApiService();
