import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
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
      setError('');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handlePay = async (supplierId) => {
    try {
      await api.post(`/api/inventory/suppliers/pay/${supplierId}`);
      fetchUnpaidSuppliers();
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
          <h2 className="card-title">Unpaid Suppliers</h2>
          {suppliers.length > 0 ? (
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
                      <button
                        onClick={() => handlePay(supplier.id)}
                        className="button button-primary"
                      >
                        Pay
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-gray-500">No unpaid suppliers found.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default PaymentTracking;