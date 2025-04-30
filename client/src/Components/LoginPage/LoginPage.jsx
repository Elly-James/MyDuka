import React, { useState, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';
import { login, register } from '../../services/auth';
import './login.css';

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true); // Toggle between login and register
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [token, setToken] = useState(''); // For registration token
  const [error, setError] = useState('');
  const { setUser } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!isLogin && password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      let response;
      if (isLogin) {
        // Login
        response = await login(email, password);
        const { access_token, redirect_to } = response.data;
        localStorage.setItem('token', access_token);
        setUser({ token: access_token, role: redirect_to.split('-')[0].toUpperCase() });
        navigate(`/${redirect_to}`);
      } else {
        // Register
        response = await register(email, password, token);
        setIsLogin(true); // Switch to login after successful registration
        setError('Registration successful! Please log in.');
      }
    } catch (err) {
      setError(err.response?.data?.msg || 'An error occurred');
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = 'http://localhost:5000/api/auth/google/login';
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-purple-900 to-indigo-800 text-white">
      {/* Left Side - Background Image and Text */}
      <div className="hidden md:flex w-1/2 flex-col justify-center items-center bg-cover bg-center" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1519681393784-d120267933ba')" }}>
        <h1 className="text-4xl font-bold mb-4">MyDuka</h1>
        <p className="text-xl">Capturing Moments, Creating Memories</p>
      </div>

      {/* Right Side - Form */}
      <div className="w-full md:w-1/2 flex flex-col justify-center items-center p-8">
        <button onClick={() => navigate('/')} className="absolute top-4 left-4 text-sm opacity-70 hover:opacity-100">
          Back to website →
        </button>
        <h2 className="text-3xl font-bold mb-2">{isLogin ? 'Log In' : 'Create an account'}</h2>
        <p className="mb-6">
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <span onClick={() => setIsLogin(!isLogin)} className="text-blue-300 cursor-pointer hover:underline">
            {isLogin ? 'Sign up' : 'Log in'}
          </span>
        </p>

        {error && <p className="text-red-400 mb-4">{error}</p>}

        <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full p-3 rounded bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-3 rounded bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          {!isLogin && (
            <>
              <input
                type="password"
                placeholder="Confirm password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full p-3 rounded bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <input
                type="text"
                placeholder="Invitation token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                className="w-full p-3 rounded bg-gray-800 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </>
          )}
          <button type="submit" className="w-full p-3 bg-purple-600 rounded hover:bg-purple-700 transition">
            {isLogin ? 'Log in' : 'Create account'}
          </button>
        </form>

        <div envieclassName="mt-6 flex items-center justify-center space-x-4">
          <p>Or {isLogin ? 'log in' : 'register'} with</p>
          <button onClick={handleGoogleLogin} className="p-2 bg-gray-700 rounded hover:bg-gray-600 flex items-center space-x-2">
            <img src="https://www.google.com/favicon.ico" alt="Google" className="w-5 h-5" />
            <span>Google</span>
          </button>
          <button className="p-2 bg-gray-700 rounded hover:bg-gray-600 flex items-center space-x-2">
            <img src="https://www.apple.com/favicon.ico" alt="Apple" className="w-5 h-5" />
            <span>Apple</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;