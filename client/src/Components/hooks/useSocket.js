import { useEffect, useState, useContext } from 'react';
import { io } from 'socket.io-client';
import { api, API_BASE_URL } from '../utils/api';
import { AuthContext } from '../context/AuthContext';

const useSocket = () => {
  const [socket, setSocket] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const maxRetries = 5;
  const { user, logout } = useContext(AuthContext);

  const refreshToken = async () => {
    try {
      const response = await api.post('/api/auth/refresh');
      const newToken = response.data.access_token;
      localStorage.setItem('token', newToken);
      if (!import.meta.env.PROD) {
        console.log('Token refreshed successfully');
      }
      return newToken;
    } catch (err) {
      console.error('Failed to refresh token:', err);
      logout();
      return null;
    }
  };

  const connectSocket = async (token) => {
    const corsOrigins = import.meta.env.VITE_CORS_ORIGINS || 'http://localhost:5173';
    const socketInstance = io(API_BASE_URL, {
      query: { token: `Bearer ${token}` },
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      withCredentials: true,
      cors: {
        origin: corsOrigins.split(','),
        credentials: true,
      },
      reconnection: false, // Handle reconnection manually
    });

    socketInstance.on('connect', () => {
      if (!import.meta.env.PROD) {
        console.log('WebSocket connected, socket ID:', socketInstance.id);
      }
      setRetryCount(0);
    });

    socketInstance.on('connect_error', async (err) => {
      if (!import.meta.env.PROD) {
        console.error('WebSocket connection error:', err.message);
      }
      if (retryCount < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 5000);
        setTimeout(async () => {
          const newToken = await refreshToken();
          if (newToken) {
            setRetryCount((prev) => prev + 1);
            socketInstance.close();
            connectSocket(newToken);
          }
        }, delay);
      } else {
        console.error('Max WebSocket retry attempts reached');
        socketInstance.close();
        setSocket(null);
      }
    });

    socketInstance.on('disconnect', (reason) => {
      if (!import.meta.env.PROD) {
        console.log('WebSocket disconnected:', reason);
      }
      if (reason === 'io server disconnect' && retryCount < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 5000);
        setTimeout(async () => {
          const newToken = await refreshToken();
          if (newToken) {
            setRetryCount((prev) => prev + 1);
            socketInstance.close();
            connectSocket(newToken);
          }
        }, delay);
      }
    });

    socketInstance.onAny((event, ...args) => {
      if (!import.meta.env.PROD) {
        console.log(`WebSocket event received: ${event}`, args);
      }
      if (event === 'report_updated') {
        const [reportType] = args;
        if (!import.meta.env.PROD) {
          console.log(`Report updated: ${reportType}`, args);
        }
      }
      if (event === 'user_invited') {
        if (!import.meta.env.PROD) {
          console.log('User invited event received:', args);
        }
      }
    });

    setSocket(socketInstance);
    return socketInstance;
  };

  useEffect(() => {
    if (!user?.token) return;

    let socketInstance;
    const initializeSocket = async () => {
      socketInstance = await connectSocket(user.token);
    };
    initializeSocket();

    return () => {
      if (socketInstance && typeof socketInstance.close === 'function') {
        socketInstance.close();
        if (!import.meta.env.PROD) {
          console.log('WebSocket closed on cleanup');
        }
      }
      setSocket(null);
    };
  }, [user?.token]);

  return { socket };
};

export default useSocket;