import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { api, handleApiError, ROUTES } from '../utils/api';
import './login.css';

const ResetPassword = () => {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const query = new URLSearchParams(location.search);
  const token = query.get('token');

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setMessage('');
    setError('');
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    try {
      const response = await api.post('/api/auth/reset-password', { token, password });
      console.log('Reset Password Response:', response.data);
      setMessage(response.data.message || 'Password reset successfully');
      setTimeout(() => navigate(ROUTES.LOGIN), 2000);
    } catch (err) {
      const errorMessage = handleApiError(err, setError);
      console.error('Reset Password Error:', errorMessage);
    }
  };

  return (
    <div className="login-container">
      <div className="form-section centered">
        <h2>Reset Password</h2>
        <form onSubmit={handleResetPassword} className="auth-form">
          <div className="password-wrapper">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="New Password"
              required
            />
            <span className="eye-icon"></span>
          </div>
          <div className="password-wrapper">
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Confirm Password"
              required
            />
            <span className="eye-icon"></span>
          </div>
          <button type="submit" className="submit-button">
            Reset Password
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

export default ResetPassword;