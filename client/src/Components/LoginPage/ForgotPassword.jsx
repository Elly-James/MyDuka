import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, handleApiError, ROUTES } from '../utils/api';
import './login.css';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');
    try {
      const response = await api.post('/api/auth/forgot-password', { email });
      console.log('Forgot Password Response:', response.data);
      setMessage(response.data.message || 'Password reset email sent');
    } catch (err) {
      const errorMessage = handleApiError(err, setError);
      console.error('Forgot Password Error:', errorMessage);
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
          Back to <Link to={ROUTES.LOGIN} className="toggle-link">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default ForgotPassword;