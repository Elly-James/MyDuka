import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, handleApiError, formatCurrency } from '../utils/api';
import SideBar from './SideBar';
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
      setError('');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  return (
    <div className="merchant-container">
      <SideBar />
      <div className="main-content">
        {error && <p className="error">{error}</p>}
        <div className="card">
          <h2 className="card-title">Store Reports</h2>
          {stores.length > 0 ? (
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
                    <td>{formatCurrency(store.total_revenue, 'KSH')}</td>
                    <td>{store.total_quantity_sold}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-gray-500">No store reports found.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default StoreReports;