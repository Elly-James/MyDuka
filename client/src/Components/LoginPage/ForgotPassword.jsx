import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../utils/api';
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
      setError(err.response?.data?.message || 'Failed to send reset email');
      setMessage('');
    }
  };

  return (
    <div className="forgot-password-container">
      <div className="form-box">
        <h2>Forgot Password</h2>
        <form onSubmit={handleForgotPassword}>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email"
            required
          />
          <button type="submit">Send Reset Link</button>
        </form>
        {message && <p>{message}</p>}
        {error && <p className="error">{error}</p>}
        <p>
          Back to <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default ForgotPassword;