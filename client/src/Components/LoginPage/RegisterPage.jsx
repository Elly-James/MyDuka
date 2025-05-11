import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { api, handleApiError, ROUTES } from '../utils/api';
import './login.css';

const RegisterPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const query = new URLSearchParams(location.search);
  const token = query.get('token') || '';

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (!termsAccepted) {
      setError('You must agree to the Terms & Conditions');
      return;
    }
    try {
      const response = await api.post('/api/auth/register', { email, password, token });
      console.log('Register Response:', response.data);
      navigate(ROUTES.LOGIN, { state: { message: 'Registration successful! Please log in.' } });
    } catch (err) {
      const errorMessage = handleApiError(err, setError);
      console.error('Register Error:', errorMessage);
    }
  };

  return (
    <div className="login-container">
      <div className="form-section centered">
        <h2>Register</h2>
        <form onSubmit={handleRegister} className="auth-form">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
          />
          <div className="password-wrapper">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />
            <span className="eye-icon"></span>
          </div>
          <div className="password-wrapper">
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm password"
              required
            />
            <span className="eye-icon"></span>
          </div>
          <input
            type="text"
            value={token}
            onChange={(e) => setError('Token should be provided via URL')}
            placeholder="Invitation token"
            required
            disabled
          />
          <label className="terms-checkbox">
            <input
              type="checkbox"
              checked={termsAccepted}
              onChange={(e) => setTermsAccepted(e.target.checked)}
            />
            I agree to the <span>Terms & Conditions</span>
          </label>
          <button type="submit" className="submit-button">
            Register
          </button>
        </form>
        {error && <p className="error">{error}</p>}
        <p className="toggle-text">
          Already have an account? <Link to={ROUTES.LOGIN} className="toggle-link">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;