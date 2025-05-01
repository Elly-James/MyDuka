import React, { createContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ROLES, ROUTES } from '../utils/api';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const response = await api.get('/api/auth/me');
          const userData = response.data;
          setUser({
            token,
            role: userData.role.replace('UserRole.', ''), // Remove the 'UserRole.' prefix
            name: userData.name,
            email: userData.email,
            store_id: userData.store_id,
          });
        } catch (err) {
          console.error('Auth initialization failed:', err);
          localStorage.removeItem('token');
          setUser(null);
        }
      }
      setLoading(false);
    };
    initializeAuth();
  }, []);

  const login = async (token, userData) => {
    console.log('Login called with:', { token, userData });
    const normalizedRole = userData.role.replace('UserRole.', ''); // Normalize the role
    localStorage.setItem('token', token);
    setUser({
      token,
      role: normalizedRole,
      name: userData.name,
      email: userData.email,
      store_id: userData.store_id,
    });
    console.log('User state set:', {
      token,
      role: normalizedRole,
      name: userData.name,
      email: userData.email,
      store_id: userData.store_id,
    });
    console.log('Navigating to role:', normalizedRole);
    setTimeout(() => {
      switch (normalizedRole) {
        case ROLES.MERCHANT:
          console.log('Navigating to MERCHANT_DASHBOARD');
          navigate(ROUTES.MERCHANT_DASHBOARD, { replace: true });
          break;
        case ROLES.ADMIN:
          console.log('Navigating to ADMIN_DASHBOARD');
          navigate(ROUTES.ADMIN_DASHBOARD, { replace: true });
          break;
        case ROLES.CLERK:
          console.log('Navigating to CLERK_STOCK_ENTRY');
          navigate(ROUTES.CLERK_STOCK_ENTRY, { replace: true });
          break;
        default:
          console.log('Navigating to LOGIN (default)');
          navigate(ROUTES.LOGIN, { replace: true });
      }
    }, 100);
  };

  const logout = () => {
    console.log('Logging out');
    localStorage.removeItem('token');
    setUser(null);
    navigate(ROUTES.LOGIN);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};