import React from 'react';

const ImageUploader = ({ onImageChange }) => {
  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onImageChange(e.target.files[0]);
    }
  };

  return (
    <div className="form-group" style={{ marginTop: '1.5rem' }}>
      <label htmlFor="image-upload"><strong>Upload an image (optional):</strong></label>
      <input
        type="file"
        id="image-upload"
        accept="image/*"
        onChange={handleChange}
        className="file-input"
        style={{ marginTop: '0.5rem', display: 'block' }}
      />
      <p className="help-text">Clear, well-lit photos of the affected area help provide better guidance.</p>
    </div>
  );
};

export default ImageUploader;
