import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../utils/api';
import './merchant.css';

const StoreReports = () => {
  const [stores, setStores] = useState([]);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchStoreReports();
  }, []);

  const fetchStoreReports = async () => {
    try {
      const response = await api.get('/api/reports/stores');
      setStores(response.data.stores || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to fetch store reports');
    }
  };

  return (
    <div className="merchant-container">
      <div className="sidebar">
        <h3>Merchant Dashboard</h3>
        <a onClick={() => navigate('/merchant/dashboard')}>Dashboard</a>
        <a onClick={() => navigate('/merchant/admin-management')}>Admin Management</a>
        <a onClick={() => navigate('/merchant/payment-tracking')}>Payment Tracking</a>
        <a onClick={() => navigate('/merchant/store-reports')}>Store Reports</a>
      </div>
      <div className="main-content">
        <div className="store-reports">
          <h1>Store Reports</h1>
          <table>
            <thead>
              <tr>
                <th>Store ID</th>
                <th>Name</th>
                <th>Total Revenue</th>
                <th>Total Quantity Sold</th>
              </tr>
            </thead>
            <tbody>
              {stores.map((store) => (
                <tr key={store.id}>
                  <td>{store.id}</td>
                  <td>{store.name}</td>
                  <td>{store.total_revenue}</td>
                  <td>{store.total_quantity_sold}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    </div>
  );
};

export default StoreReports;