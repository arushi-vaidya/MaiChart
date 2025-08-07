// API base URL - using proxy in package.json for development
const API_BASE_URL = '/api';

// API service class to handle all backend communication including medical extraction
class ApiService {
  // Upload audio file for transcription - FIXED VERSION
  async uploadAudio(file, onProgress = null) {
    const formData = new FormData();
    
    // Ensure we have a proper file object
    if (!file) {
      throw new Error('No file provided');
    }

    // Log file details for debugging
    console.log('Preparing to upload:', {
      name: file.name || 'unnamed',
      size: file.size,
      type: file.type,
      isBlob: file instanceof Blob,
      isFile: file instanceof File
    });

    // Add the file to FormData with proper field name
    formData.append('audio', file, file.name || 'recording.webm');
    formData.append('timestamp', Date.now().toString());

    // Debug FormData contents
    console.log('FormData entries:');
    for (let [key, value] of formData.entries()) {
      console.log(key, value);
    }

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
        console.log('Upload response status:', xhr.status);
        console.log('Upload response text:', xhr.responseText);
        
        if (xhr.status === 200) {
          try {
            const result = JSON.parse(xhr.responseText);
            resolve(result);
          } catch (e) {
            console.error('JSON parse error:', e);
            reject(new Error('Invalid response format'));
          }
        } else {
          // Try to parse error response
          try {
            const errorResponse = JSON.parse(xhr.responseText);
            reject(new Error(errorResponse.error || `Upload failed: ${xhr.status} ${xhr.statusText}`));
          } catch (e) {
            reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
          }
        }
      });

      xhr.addEventListener('error', () => {
        console.error('Upload network error');
        reject(new Error('Upload failed due to network error'));
      });

      xhr.addEventListener('timeout', () => {
        console.error('Upload timeout');
        reject(new Error('Upload timed out'));
      });

      // Start upload with proper headers
      xhr.open('POST', `${API_BASE_URL}/upload_audio`);
      xhr.timeout = 600000; // 10 minutes timeout

      // Don't set Content-Type header - let browser set it with boundary for multipart/form-data
      
      console.log('Starting upload to:', `${API_BASE_URL}/upload_audio`);
      xhr.send(formData);
    });
  }

  // Get processing status for a session
  async getStatus(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/status/${sessionId}`);
      console.log('Status response:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Status error response:', errorText);
        throw new Error(`Status check failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Status check error:', error);
      throw error;
    }
  }

  // Get transcript for a session
  async getTranscript(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/transcript/${sessionId}`);
      console.log('Transcript response:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Transcript error response:', errorText);
        throw new Error(`Transcript retrieval failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Transcript retrieval error:', error);
      throw error;
    }
  }

  // NEW: Get medical data for a session
  async getMedicalData(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/medical_data/${sessionId}`);
      console.log('Medical data response:', response.status);
      
      if (response.status === 404) {
        // Medical data not found - this is normal if extraction hasn't completed yet
        return null;
      }
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Medical data error response:', errorText);
        throw new Error(`Medical data retrieval failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Medical data retrieval error:', error);
      // Don't throw for medical data - it's optional
      return null;
    }
  }

  // NEW: Get medical summary for a session
  async getMedicalSummary(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/medical_summary/${sessionId}`);
      if (response.status === 404) {
        return null;
      }
      if (!response.ok) {
        throw new Error(`Medical summary retrieval failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Medical summary retrieval error:', error);
      return null;
    }
  }

  // NEW: Get medical alerts for a session
  async getMedicalAlerts(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/medical_alerts/${sessionId}`);
      if (response.status === 404) {
        return null;
      }
      if (!response.ok) {
        throw new Error(`Medical alerts retrieval failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Medical alerts retrieval error:', error);
      return null;
    }
  }

  // NEW: Download medical data as JSON
  async downloadMedicalData(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/medical_data/${sessionId}/download`);
      if (!response.ok) {
        throw new Error(`Medical data download failed: ${response.status}`);
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `medical_data_${sessionId.substring(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Medical data download error:', error);
      throw error;
    }
  }

  // NEW: Trigger medical extraction manually
  async triggerMedicalExtraction(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/trigger_medical_extraction/${sessionId}`, {
        method: 'POST'
      });
      if (!response.ok) {
        throw new Error(`Medical extraction trigger failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Medical extraction trigger error:', error);
      throw error;
    }
  }

  // Download transcript as file
  async downloadTranscript(sessionId) {
    try {
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
    } catch (error) {
      console.error('Download error:', error);
      throw error;
    }
  }

  // Get all notes
  async getAllNotes() {
    try {
      const response = await fetch(`${API_BASE_URL}/notes`);
      if (!response.ok) {
        throw new Error(`Failed to fetch notes: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Get all notes error:', error);
      throw error;
    }
  }

  // Search notes
  async searchNotes(query) {
    try {
      const response = await fetch(`${API_BASE_URL}/notes/search?q=${encodeURIComponent(query)}`);
      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Search notes error:', error);
      throw error;
    }
  }

  // Get notes statistics
  async getNotesStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/notes/stats`);
      if (!response.ok) {
        throw new Error(`Stats retrieval failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Get notes stats error:', error);
      throw error;
    }
  }

  // NEW: Get medical extraction statistics
  async getMedicalStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/medical_stats`);
      if (!response.ok) {
        throw new Error(`Medical stats retrieval failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Get medical stats error:', error);
      throw error;
    }
  }

  // Delete a session
  async deleteSession(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/cleanup/${sessionId}`, {
        method: 'DELETE'
      });
      if (!response.ok) {
        throw new Error(`Delete failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Delete session error:', error);
      throw error;
    }
  }

  // Export all notes
  async exportNotes() {
    try {
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
    } catch (error) {
      console.error('Export notes error:', error);
      throw error;
    }
  }

  // Health check
  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Health check error:', error);
      throw error;
    }
  }

  // Get system stats
  async getSystemStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/stats`);
      if (!response.ok) {
        throw new Error(`Stats failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Get system stats error:', error);
      throw error;
    }
  }
}

// Export singleton instance
export default new ApiService();