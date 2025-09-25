const API_BASE_URL = 'http://localhost:5001/api';

class ApiService {
  async uploadAudio(file, onProgress = null) {
    console.log('USING URL:', API_BASE_URL);
    
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
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error'));
      });

      xhr.open('POST', API_BASE_URL + '/upload_audio');
      xhr.send(formData);
    });
  }

  async getStatus(sessionId) {
    const response = await fetch(`${API_BASE_URL}/status/${sessionId}`);
    return response.json();
  }

  async getMedicalData(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/medical_data/${sessionId}`);
      if (response.status === 404) return null;
      return response.json();
    } catch { return null; }
  }

  async getAllNotes() {
    const response = await fetch(`${API_BASE_URL}/notes`);
    return response.json();
  }

  async deleteSession(sessionId) {
    const response = await fetch(`${API_BASE_URL}/cleanup/${sessionId}`, { method: 'DELETE' });
    return response.json();
  }
}

export default new ApiService();
