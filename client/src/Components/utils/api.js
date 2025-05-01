import axios from 'axios';

// Constants
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'; // Fallback to localhost if env var is not set

const ROLES = {
  MERCHANT: 'MERCHANT',
  ADMIN: 'ADMIN',
  CLERK: 'CLERK',
};

const ROUTES = {
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  MERCHANT_DASHBOARD: '/merchant/dashboard',
  MERCHANT_ADMIN_MANAGEMENT: '/merchant/admin-management',
  MERCHANT_PAYMENT_TRACKING: '/merchant/payment-tracking',
  MERCHANT_STORE_REPORTS: '/merchant/store-reports',
  ADMIN_DASHBOARD: '/admin/dashboard',
  ADMIN_CLERK_MANAGEMENT: '/admin/clerk-management',
  ADMIN_INVENTORY: '/admin/inventory',
  ADMIN_PAYMENTS: '/admin/payments',
  ADMIN_REPORTS: '/admin/reports',
  ADMIN_SUPPLY_REQUESTS: '/admin/supply-requests',
  CLERK_ACTIVITY_LOG: '/clerk/activity-log',
  CLERK_STOCK_ALERTS: '/clerk/stock-alerts',
  CLERK_STOCK_ENTRY: '/clerk/stock-entry',
};

// Helper Functions
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

const formatCurrency = (amount, currency = 'KSH') => {
  return `${currency} ${parseFloat(amount).toFixed(2)}`;
};

const handleApiError = (error, setError) => {
  const message = error.response?.data?.message || error.message || 'An error occurred';
  setError(message);
};

// Axios Setup
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = ROUTES.LOGIN;
    }
    return Promise.reject(error);
  }
);

// Export all
export { api, API_BASE_URL, ROLES, ROUTES, formatDate, formatCurrency, handleApiError };