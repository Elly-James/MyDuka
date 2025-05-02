import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, handleApiError, formatCurrency } from '../utils/api';
import SideBar from './SideBar';
import './merchant.css';

const StoreReports = () => {
  const [stores, setStores] = useState([]);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState('weekly');
  const navigate = useNavigate();

  useEffect(() => {
    fetchStoreReports();
  }, []);

  const fetchStoreReports = async () => {
    try {
      const response = await api.get(`/api/reports/stores?period=${period}`);
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
        {error && <p className="text-red-500 mb-4">{error}</p>}

        <div className="card">
          <h2 className="card-title">Store Reports</h2>
          <div className="flex justify-between mb-4">
            <div className="flex gap-2">
              <button
                className={`button ${period === 'weekly' ? 'button-primary active' : 'button-primary'}`}
                onClick={() => { setPeriod('weekly'); fetchStoreReports(); }}
              >
                Weekly
              </button>
              <button
                className={`button ${period === 'monthly' ? 'button-primary active' : 'button-primary'}`}
                onClick={() => { setPeriod('monthly'); fetchStoreReports(); }}
              >
                Monthly
              </button>
              <button
                className={`button ${period === 'annual' ? 'button-primary active' : 'button-primary'}`}
                onClick={() => { setPeriod('annual'); fetchStoreReports(); }}
              >
                Annual
              </button>
            </div>
            <button className="button button-primary">EXPORT PDF</button>
          </div>
          <table className="table">
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
        </div>
      </div>
    </div>
  );
};

export default StoreReports;