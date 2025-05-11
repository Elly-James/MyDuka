import axios from 'axios';
import { formatDate, formatCurrency } from './formatters';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const ROLES = {
  MERCHANT: 'MERCHANT',
  ADMIN: 'ADMIN',
  CLERK: 'CLERK',
};

const ROUTES = {
  LOGIN: '/login',
  MERCHANT_DASHBOARD: '/merchant/dashboard',
  API_STORES: '/api/stores',
  API_REPORTS_SALES: '/api/reports/sales',
  API_REPORTS_SPOILAGE: '/api/reports/spoilage',
  API_REPORTS_TOP_PRODUCTS: '/api/reports/top-products',
  API_REPORTS_EXPORT: '/api/reports/export',
  API_DASHBOARD_SUMMARY: '/api/dashboard/summary',
  API_NOTIFICATIONS: '/api/notifications',
};

const handleApiError = (error, setError) => {
  let message;
  if (error.response) {
    const { status, data } = error.response;
    if (data.message) {
      switch (data.message) {
        case 'No accessible stores for this user':
          message = 'No stores available for your account.';
          break;
        case 'Invalid period. Use weekly or monthly':
          message = 'Invalid period selected.';
          break;
        case 'Unauthorized':
          message = 'You do not have permission to access this resource.';
          break;
        case 'Internal server error':
          message = 'A server error occurred. Please try again later.';
          break;
        default:
          message = data.message;
      }
    } else {
      message =
        status === 400
          ? 'Invalid request. Please check your input.'
          : status === 401
          ? 'Unauthorized. Please log in again.'
          : status === 403
          ? 'Access forbidden.'
          : status === 404
          ? 'Resource not found.'
          : status === 429
          ? 'Too many requests. Please try again later.'
          : 'An error occurred. Please try again.';
    }
  } else if (error.request) {
    message = 'No response from server. Please check your network.';
  } else {
    message = error.message || 'An unexpected error occurred.';
  }

  if (!import.meta.env.PROD) {
    console.error('API Error:', {
      message,
      status: error.response?.status,
      data: error.response?.data,
    });
  }

  if (setError) {
    setError(message);
  }
  return message;
};

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  },
  withCredentials: true,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 429) {
      const retryAfter = parseInt(error.response.headers['retry-after'] || 1000, 10);
      await new Promise((resolve) => setTimeout(resolve, retryAfter));
      return api(error.config);
    }
    if (error.response?.status === 401 || error.response?.status === 422) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = ROUTES.LOGIN;
    }
    return Promise.reject(error);
  }
);

export { api, API_BASE_URL, ROLES, ROUTES, formatDate, formatCurrency, handleApiError };