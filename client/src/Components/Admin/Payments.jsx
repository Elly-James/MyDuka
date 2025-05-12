// src/Components/Admin/Payments.jsx
import React, { useState, useEffect } from 'react';
import { api, handleApiError, formatCurrency } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './admin.css';

const Payments = () => {
  const [payments, setPayments] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [activeTab, setActiveTab] = useState('unpaid');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [stats, setStats] = useState({
    total_unpaid: 0,
    total_paid: 0
  });

  useEffect(() => {
    const fetchPayments = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/payments');
        const data = response.data;
        
        setPayments(data.payments);
        setStats({
          total_unpaid: data.total_unpaid,
          total_paid: data.total_paid
        });
        
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchPayments();
  }, []);

  useEffect(() => {
    const filteredList = payments.filter(payment => {
      const matchesTab = payment.status === activeTab;
      const matchesSearch = payment.supplier_name.toLowerCase().includes(search.toLowerCase());
      return matchesTab && matchesSearch;
    });
    setFiltered(filteredList);
  }, [activeTab, search, payments]);

  const handleMarkAsPaid = async (paymentId) => {
    try {
      await api.put(`/api/payments/${paymentId}/mark-paid`);
      setPayments(payments.map(p => 
        p.id === paymentId ? { ...p, status: 'paid' } : p
      ));
      setStats(prev => ({
        total_unpaid: prev.total_unpaid - p.amount,
        total_paid: prev.total_paid + p.amount
      }));
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  return (
    <div className="admin-container">
      <SideBar />
      <div className="main-content">
        <NavBar />
        
        {error && <div className="alert error">{error}</div>}
        {loading && <div className="loading">Loading payments...</div>}

        <h1>Payment Tracking</h1>
        
        <div className="stats">
          <div className="stat-card">
            <h3>Total Unpaid</h3>
            <p className="amount unpaid">{formatCurrency(stats.total_unpaid)}</p>
          </div>
          <div className="stat-card">
            <h3>Total Paid</h3>
            <p className="amount paid">{formatCurrency(stats.total_paid)}</p>
          </div>
        </div>
        
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'unpaid' ? 'active' : ''}`}
            onClick={() => setActiveTab('unpaid')}
          >
            Unpaid
          </button>
          <button
            className={`tab ${activeTab === 'paid' ? 'active' : ''}`}
            onClick={() => setActiveTab('paid')}
          >
            Paid
          </button>
        </div>
        
        <div className="search-container">
          <input
            type="text"
            placeholder="Search suppliers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Product</th>
                <th>Amount</th>
                <th>Due Date</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(payment => (
                <tr key={payment.id}>
                  <td>{payment.supplier_name}</td>
                  <td>{payment.product_name}</td>
                  <td>{formatCurrency(payment.amount)}</td>
                  <td>{new Date(payment.due_date).toLocaleDateString()}</td>
                  <td>
                    <span className={`badge ${payment.status === 'paid' ? 'success' : 'warning'}`}>
                      {payment.status}
                    </span>
                  </td>
                  <td>
                    {payment.status === 'unpaid' && (
                      <button 
                        onClick={() => handleMarkAsPaid(payment.id)}
                        className="btn-sm success"
                      >
                        Mark as Paid
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Payments;