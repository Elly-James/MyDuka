import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { api, handleApiError, ROUTES } from '../utils/api';
import './login.css';

const RegisterPage = () => {
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    password: '',
    confirmPassword: ''
  });
  const [token, setToken] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [invitation, setInvitation] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Extract token and email from URL
  useEffect(() => {
    const query = new URLSearchParams(location.search);
    const urlToken = query.get('token');
    const urlEmail = query.get('email');

    if (!urlToken || !urlEmail) {
      setError('Invalid registration link - missing token or email');
      setLoading(false);
      return;
    }

    setToken(urlToken);
    setFormData(prev => ({ ...prev, email: urlEmail }));

    // Verify the token
    const verifyToken = async () => {
      try {
        const response = await api.get(`/api/auth/register?token=${urlToken}&email=${urlEmail}`);
        
        if (response.data.status === 'success') {
          setInvitation(response.data.invitation);
        } else {
          setError(response.data.message || 'Invalid invitation');
        }
      } catch (err) {
        let errorMessage = 'Failed to verify invitation';
        
        // Handle specific error codes
        if (err.response?.data?.code) {
          switch(err.response.data.code) {
            case 'EXPIRED_TOKEN':
              errorMessage = 'This invitation link has expired';
              break;
            case 'USED_TOKEN':
              errorMessage = 'This invitation has already been used';
              break;
            case 'INVALID_STATUS':
              errorMessage = 'This invitation is no longer valid';
              break;
            default:
              errorMessage = err.response.data.message || errorMessage;
          }
        } else {
          errorMessage = handleApiError(err, setError);
        }
        
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    verifyToken();
  }, [location.search]);

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    // Validate form
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (!termsAccepted) {
      setError('You must agree to the Terms & Conditions');
      return;
    }
    if (!formData.name) {
      setError('Name is required');
      return;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    try {
      const response = await api.post('/api/auth/register', {
        token,
        email: formData.email,
        name: formData.name,
        password: formData.password
      });

      if (response.data.status === 'success') {
        // Store tokens and redirect
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        
        // Redirect to appropriate dashboard
        navigate(response.data.redirect_to || `/${response.data.user?.role?.toLowerCase()}-dashboard`);
      } else {
        setError(response.data.message || 'Registration failed');
      }
    } catch (err) {
      let errorMessage = 'Registration failed';
      
      if (err.response?.data?.code) {
        switch(err.response.data.code) {
          case 'EMAIL_EXISTS':
            errorMessage = 'This email is already registered';
            break;
          case 'EXPIRED_TOKEN':
            errorMessage = 'Invitation expired during registration';
            break;
          case 'USED_TOKEN':
            errorMessage = 'Invitation was already used';
            break;
          default:
            errorMessage = err.response.data.message || errorMessage;
        }
      } else {
        errorMessage = handleApiError(err, setError);
      }
      
      setError(errorMessage);
    }
  };

  if (loading) {
    return (
      <div className="login-container">
        <div className="form-section centered">
          <h2>Verifying invitation...</h2>
          <p>Please wait while we verify your invitation link</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="login-container">
        <div className="form-section centered">
          <h2>Registration Error</h2>
          <p className="error">{error}</p>
          <p className="toggle-text">
            <Link to={ROUTES.LOGIN} className="toggle-link">Back to Login</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="form-section centered">
        <h2>Complete Registration</h2>
        {invitation && (
          <div className="invitation-info">
            <p>You're registering as a <strong>{invitation.role.toLowerCase()}</strong></p>
            {invitation.store && (
              <p>for <strong>{invitation.store.name}</strong></p>
            )}
          </div>
        )}
        
        <form onSubmit={handleRegister} className="auth-form">
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            placeholder="Email"
            required
            disabled
          />
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            placeholder="Your Full Name"
            required
          />
          <div className="password-wrapper">
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              placeholder="Password (min 8 characters)"
              required
              minLength={8}
            />
          </div>
          <div className="password-wrapper">
            <input
              type="password"
              value={formData.confirmPassword}
              onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
              placeholder="Confirm Password"
              required
              minLength={8}
            />
          </div>
          <label className="terms-checkbox">
            <input
              type="checkbox"
              checked={termsAccepted}
              onChange={(e) => setTermsAccepted(e.target.checked)}
              required
            />
            I agree to the <Link to={ROUTES.TERMS} target="_blank">Terms & Conditions</Link>
          </label>
          <button type="submit" className="submit-button">
            Complete Registration
          </button>
        </form>
        <p className="toggle-text">
          Already have an account? <Link to={ROUTES.LOGIN} className="toggle-link">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;