// src/Components/LoginPage/ForgotPassword.jsx
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, handleApiError } from '../utils/api'; // Correct path
import './login.css';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post('/api/auth/forgot-password', { email });
      setMessage(response.data.message || 'Password reset email sent');
      setError('');
    } catch (err) {
      handleApiError(err, setError);
      setMessage('');
    }
  };

  return (
    <div className="login-container">
      <div className="form-section centered">
        <h2>Forgot Password</h2>
        <form onSubmit={handleForgotPassword} className="auth-form">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            required
          />
          <button type="submit" className="submit-button">
            Send Reset Link
          </button>
        </form>
        {message && <p className="success">{message}</p>}
        {error && <p className="error">{error}</p>}
        <p className="toggle-text">
          Back to <Link to="/login" className="toggle-link">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default ForgotPassword;