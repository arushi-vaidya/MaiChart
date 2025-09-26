// Fixed API service with environment-aware URL configuration
const getApiBaseUrl = () => {
  // Check if we have a React environment variable
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // Auto-detect based on environment
  const { protocol, hostname, port } = window.location;
  
  // In development (localhost)
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:5001/api';
  }
  
  // In Docker/production - use current host with api path
  return `${protocol}//${hostname}${port ? `:${port}` : ''}/api`;
};

const API_BASE_URL = getApiBaseUrl();

class ApiService {
  constructor() {
    console.log('🌐 API Service initialized with base URL:', API_BASE_URL);
  }

  async uploadAudio(file, onProgress = null) {
    const formData = new FormData();
    if (!file) throw new Error('No file provided');
    
    formData.append('audio', file, file.name || 'recording.webm');
    formData.append('timestamp', Date.now().toString());

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            onProgress((event.loaded / event.total) * 100);
          }
        });
      }

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new Error(`Upload failed: ${xhr.status} - ${xhr.statusText}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      xhr.open('POST', `${API_BASE_URL}/upload_audio`);
      xhr.send(formData);
    });
  }

  async getStatus(sessionId) {
    const response = await fetch(`${API_BASE_URL}/status/${sessionId}`);
    if (!response.ok) {
      throw new Error(`Status check failed: ${response.status}`);
    }
    return response.json();
  }

  async getMedicalData(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/medical_data/${sessionId}`);
      if (response.status === 404) return null;
      if (!response.ok) {
        throw new Error(`Medical data fetch failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Error fetching medical data:', error);
      return null;
    }
  }

  async getMedicalAlerts(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/medical_alerts/${sessionId}`);
      if (response.status === 404) return { alerts: [] };
      if (!response.ok) {
        throw new Error(`Medical alerts fetch failed: ${response.status}`);
      }
      return response.json();
    } catch (error) {
      console.error('Error fetching medical alerts:', error);
      return { alerts: [] };
    }
  }

  async triggerMedicalExtraction(sessionId) {
    const response = await fetch(`${API_BASE_URL}/trigger_medical_extraction/${sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      throw new Error(`Trigger extraction failed: ${response.status}`);
    }
    return response.json();
  }

  async downloadTranscript(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/transcript/${sessionId}/download`);
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `medical_transcript_${sessionId.substring(0, 8)}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading transcript:', error);
      throw error;
    }
  }

  // FIXED: Added missing downloadMedicalData method
  async downloadMedicalData(sessionId) {
    try {
      // First get the medical data
      const medicalResponse = await this.getMedicalData(sessionId);
      if (!medicalResponse?.medical_data) {
        throw new Error('No medical data available for download');
      }

      // Format as JSON for download
      const medicalJson = JSON.stringify(medicalResponse.medical_data, null, 2);
      const blob = new Blob([medicalJson], { type: 'application/json' });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `medical_data_${sessionId.substring(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading medical data:', error);
      throw error;
    }
  }

  async getAllNotes() {
    const response = await fetch(`${API_BASE_URL}/notes`);
    if (!response.ok) {
      throw new Error(`Get notes failed: ${response.status}`);
    }
    return response.json();
  }

  async deleteSession(sessionId) {
    const response = await fetch(`${API_BASE_URL}/cleanup/${sessionId}`, { 
      method: 'DELETE' 
    });
    if (!response.ok) {
      throw new Error(`Delete session failed: ${response.status}`);
    }
    return response.json();
  }

  // Utility method to get current API base URL
  getApiBaseUrl() {
    return API_BASE_URL;
  }

  // Health check method
  async healthCheck() {
    try {
      const response = await fetch(`${API_BASE_URL}/../health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export default new ApiService();