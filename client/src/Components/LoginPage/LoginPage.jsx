import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { api, API_BASE_URL, handleApiError } from '../utils/api';
import './login.css';

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [token, setToken] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState('');
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    console.log('Form submitted');

    if (!isLogin) {
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        console.log('Error: Passwords do not match');
        return;
      }
      if (!termsAccepted) {
        setError('You must agree to the Terms & Conditions');
        console.log('Error: Terms not accepted');
        return;
      }
    }

    try {
      console.log('Sending API request:', { email, password });
      if (isLogin) {
        const response = await api.post('/api/auth/login', { email, password });
        console.log('API response:', response.data);
        const { access_token, user } = response.data;
        login(access_token, user);
      } else {
        const response = await api.post('/api/auth/register', { email, password, token });
        console.log('Registration response:', response.data);
        setIsLogin(true);
        setError('Registration successful! Please log in.');
        setEmail('');
        setPassword('');
        setConfirmPassword('');
        setToken('');
        setTermsAccepted(false);
      }
    } catch (err) {
      console.error('API error:', err);
      handleApiError(err, setError);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE_URL}/api/auth/google/login`;
  };

  return (
    <div className="login-container">
      <div className="background-section">
        <h1 className="logo">MyDuka</h1>
        <p className="slogan">Capturing Moments, Creating Memories</p>
      </div>

      <div className="form-section">
        <button onClick={() => navigate('/')} className="back-to-website">
          Back to website →
        </button>
        <h2>{isLogin ? 'Log in' : 'Create an account'}</h2>
        <p className="toggle-text">
          {isLogin ? 'Don’t have an account?' : 'Already have an account?'}{' '}
          <span onClick={() => setIsLogin(!isLogin)} className="toggle-link">
            {isLogin ? 'Create an account' : 'Log in'}
          </span>
        </p>

        {error && <p className="error">{error}</p>}

        <form onSubmit={handleSubmit} className="auth-form">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <div className="password-wrapper">
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <span className="eye-icon"></span>
          </div>
          {!isLogin && (
            <>
              <div className="password-wrapper">
                <input
                  type="password"
                  placeholder="Confirm password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
                <span className="eye-icon"></span>
              </div>
              <input
                type="text"
                placeholder="Invitation token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
              />
              <label className="terms-checkbox">
                <input
                  type="checkbox"
                  checked={termsAccepted}
                  onChange={(e) => setTermsAccepted(e.target.checked)}
                />
                I agree to the <span>Terms & Conditions</span>
              </label>
            </>
          )}
          <button type="submit" className="submit-button">
            {isLogin ? 'Log in' : 'Create account'}
          </button>
        </form>

        <div className="social-login">
          <p>Or {isLogin ? 'log in' : 'register'} with</p>
          <div className="social-buttons">
            <button onClick={handleGoogleLogin} className="social-button google">
              <img src="https://www.google.com/favicon.ico" alt="Google" />
              Google
            </button>
            <button className="social-button apple">
              <img src="https://www.apple.com/favicon.ico" alt="Apple" />
              Apple
            </button>
          </div>
        </div>

        {isLogin && (
          <p className="forgot-password">
            Forgot your password?{' '}
            <Link to="/forgot-password" className="toggle-link">
              Reset it
            </Link>
          </p>
        )}
      </div>
    </div>
  );
};

export default LoginPage;