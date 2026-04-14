/**
 * Service for communicating with the MotherCare AI Backend API
 */

const API_BASE_URL = 'http://127.0.0.1:8000';

/**
 * Sends symptoms and an optional image to the backend for analysis
 * @param {string} symptoms - The text description of symptoms
 * @param {File} image - Optional image file
 * @returns {Promise<Object>} - The analysis result
 */
export const analyzeSymptoms = async (symptoms, image) => {
  const formData = new FormData();
  formData.append('symptoms', symptoms);
  
  if (image) {
    formData.append('file', image);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to connect to backend');
    }

    const json = await response.json();
    return json.data;
  } catch (error) {
    console.error('API Error:', error);
    throw new Error('Failed to connect to backend');
  }
};

/**
 * Basic health check for the API
 */
export const checkHealth = async () => {
  try {
    const response = await fetch(`http://localhost:8000/health`);
    return await response.json();
  } catch (error) {
    return { status: 'offline' };
  }
};
