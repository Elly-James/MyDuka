import React, { createContext, useState, useEffect, useCallback } from 'react';
import { api, ROLES, ROUTES } from '../utils/api';
import { jwtDecode } from 'jwt-decode';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tokenRefreshInterval, setTokenRefreshInterval] = useState(null);

  const refreshToken = useCallback(async () => {
    try {
      const response = await api.post('/api/auth/refresh');
      const newToken = response.data.access_token;

      // Get updated user data
      const userResponse = await api.get('/api/auth/me');
      const updatedUser = {
        token: newToken,
        role: userResponse.data.user.role.toUpperCase(), // Ensure uppercase
        name: userResponse.data.user.name,
        email: userResponse.data.user.email,
        store: userResponse.data.user.store || null,
        status: userResponse.data.user.status // Add status check
      };

      // Check if user is active
      if (updatedUser.status !== 'ACTIVE') {
        throw new Error('Your account is not active');
      }

      setUser(updatedUser);
      localStorage.setItem('token', newToken);
      localStorage.setItem('user', JSON.stringify(updatedUser));

      if (!import.meta.env.PROD) {
        console.log('Token refreshed successfully, user:', updatedUser);
      }
      return newToken;
    } catch (err) {
      console.error('Token refresh failed:', err);
      logout();
      return null;
    }
  }, []);

  const checkTokenExpiration = useCallback((token) => {
    if (!token) return false;
    try {
      const decoded = jwtDecode(token);
      const now = Date.now() / 1000;
      return decoded.exp < now;
    } catch (err) {
      console.error('Token decode error:', err);
      return true;
    }
  }, []);

  const initializeAuth = useCallback(async () => {
    const token = localStorage.getItem('token');
    const userData = localStorage.getItem('user');

    if (!token || !userData) {
      setLoading(false);
      return;
    }

    try {
      const parsedUser = JSON.parse(userData);

      // Check if token is expired
      if (checkTokenExpiration(token)) {
        await refreshToken();
      } else {
        // Set up token refresh before expiration
        const decoded = jwtDecode(token);
        const expiresIn = decoded.exp * 1000 - Date.now();
        const refreshTime = Math.max(expiresIn - 60000, 0);

        if (refreshTime > 0) {
          setTokenRefreshInterval(setTimeout(() => refreshToken(), refreshTime));
        }

        // Verify token with backend
        const response = await api.get('/api/auth/me');
        const serverUser = response.data.user;
        const updatedUser = {
          token,
          role: serverUser.role.toUpperCase(),
          name: serverUser.name,
          email: serverUser.email,
          store: serverUser.store || null,
          status: serverUser.status
        };

        // Check if user is active
        if (updatedUser.status !== 'ACTIVE') {
          throw new Error('Your account is not active');
        }

        setUser(updatedUser);
        localStorage.setItem('user', JSON.stringify(updatedUser));

        if (!import.meta.env.PROD) {
          console.log('Auth initialized, user:', updatedUser);
        }
      }
    } catch (err) {
      console.error('Auth initialization failed:', err);
      logout();
    } finally {
      setLoading(false);
    }
  }, [checkTokenExpiration, refreshToken]);

  useEffect(() => {
    initializeAuth();

    return () => {
      if (tokenRefreshInterval) {
        clearTimeout(tokenRefreshInterval);
      }
    };
  }, [initializeAuth]);

  const login = (token, userData) => {
    // Normalize role and store user data
    const normalizedRole = userData.role.toUpperCase();
    const newUser = {
      token,
      role: normalizedRole,
      name: userData.name,
      email: userData.email,
      store: userData.store || null,
      status: userData.status
    };

    // Store tokens and user data
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(newUser));
    setUser(newUser);

    // Set up token refresh before expiration
    const decoded = jwtDecode(token);
    const expiresIn = decoded.exp * 1000 - Date.now();
    const refreshTime = Math.max(expiresIn - 60000, 0);

    if (refreshTime > 0) {
      setTokenRefreshInterval(setTimeout(() => refreshToken(), refreshTime));
    }

    if (!import.meta.env.PROD) {
      console.log('User logged in:', newUser);
    }

    // Immediate navigation based on role
    switch (normalizedRole) {
      case ROLES.MERCHANT:
        window.location.href = ROUTES.MERCHANT_DASHBOARD;
        break;
      case ROLES.ADMIN:
        window.location.href = '/admin/clerk-management';
        break;
      case ROLES.CLERK:
        window.location.href = '/clerk/stock-entry';
        break;
      default:
        window.location.href = ROUTES.LOGIN;
    }
  };

  const logout = () => {
    if (tokenRefreshInterval) {
      clearTimeout(tokenRefreshInterval);
    }
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    window.location.href = ROUTES.LOGIN;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        loading,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};