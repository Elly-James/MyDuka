// src/Components/Clerk/StockAlerts.jsx
import React, { useState, useEffect } from 'react';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './clerk.css';

const StockAlerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/inventory/low-stock');
        
        // Safely handle the response data
        const alertsData = response.data?.alerts || response.data || [];
        setAlerts(Array.isArray(alertsData) ? alertsData : []);
        
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  const handleRequestSupply = async (productId) => {
    try {
      setLoading(true);
      await api.post('/api/supply-requests', { product_id: productId });
      setSuccess('Supply request submitted successfully');
      
      // Refresh alerts
      const response = await api.get('/api/inventory/low-stock');
      const refreshedAlerts = response.data?.alerts || response.data || [];
      setAlerts(Array.isArray(refreshedAlerts) ? refreshedAlerts : []);
      
    } catch (err) {
      handleApiError(err, setError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="clerk-container">
      <SideBar />
      <div className="main-content">
        <NavBar />
        
        {error && <div className="alert error">{error}</div>}
        {success && <div className="alert success">{success}</div>}
        {loading && <div className="loading">Loading stock alerts...</div>}

        <h1>Stock Alerts</h1>
        
        <div className="card">
          {!loading && alerts?.length === 0 ? (
            <p className="no-alerts">No low stock items at this time.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Current Stock</th>
                  <th>Minimum Required</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {alerts?.map((alert) => (
                  <tr key={alert.product_id || alert.id}>
                    <td>{alert.product_name || alert.name}</td>
                    <td className={alert.current_stock <= (alert.min_stock_level || 5) ? 'text-danger' : ''}>
                      {alert.current_stock}
                    </td>
                    <td>{alert.min_stock_level || 'N/A'}</td>
                    <td>
                      <button
                        onClick={() => handleRequestSupply(alert.product_id || alert.id)}
                        className="btn-primary"
                        disabled={loading}
                      >
                        {loading ? 'Processing...' : 'Request Supply'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default StockAlerts;