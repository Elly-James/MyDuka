import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../utils/api';
import './merchant.css';

const PaymentTracking = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchUnpaidSuppliers();
  }, []);

  const fetchUnpaidSuppliers = async () => {
    try {
      const response = await api.get('/api/inventory/suppliers/unpaid');
      setSuppliers(response.data.suppliers || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to fetch unpaid suppliers');
    }
  };

  const handlePay = async (supplierId) => {
    try {
      await api.post(`/api/inventory/suppliers/pay/${supplierId}`);
      fetchUnpaidSuppliers();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to process payment');
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
        <div className="payment-tracking">
          <h1>Payment Tracking</h1>
          <table>
            <thead>
              <tr>
                <th>Supplier ID</th>
                <th>Name</th>
                <th>Amount Due</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((supplier) => (
                <tr key={supplier.id}>
                  <td>{supplier.id}</td>
                  <td>{supplier.name}</td>
                  <td>{supplier.amount_due}</td>
                  <td>
                    <button className="pay" onClick={() => handlePay(supplier.id)}>Pay</button>
                  </td>
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

export default PaymentTracking;