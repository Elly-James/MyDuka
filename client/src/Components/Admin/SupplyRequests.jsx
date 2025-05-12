// src/Components/Admin/SupplyRequests.jsx
import React, { useState, useEffect } from 'react';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './admin.css';

const SupplyRequests = () => {
  const [requests, setRequests] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchRequests = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/supply-requests');
        setRequests(response.data.requests);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchRequests();
  }, []);

  useEffect(() => {
    const filteredList = requests.filter(request => {
      const matchesTab = request.status === activeTab;
      const matchesSearch = request.product_name.toLowerCase().includes(search.toLowerCase());
      return matchesTab && matchesSearch;
    });
    setFiltered(filteredList);
  }, [activeTab, search, requests]);

  const handleApprove = async (requestId) => {
    try {
      await api.put(`/api/supply-requests/${requestId}/approve`);
      setRequests(requests.map(req => 
        req.id === requestId ? { ...req, status: 'approved' } : req
      ));
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handleDecline = async (requestId) => {
    try {
      await api.put(`/api/supply-requests/${requestId}/decline`);
      setRequests(requests.map(req => 
        req.id === requestId ? { ...req, status: 'declined' } : req
      ));
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
        {loading && <div className="loading">Loading requests...</div>}

        <h1>Supply Requests</h1>
        
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
            onClick={() => setActiveTab('pending')}
          >
            Pending
          </button>
          <button
            className={`tab ${activeTab === 'approved' ? 'active' : ''}`}
            onClick={() => setActiveTab('approved')}
          >
            Approved
          </button>
          <button
            className={`tab ${activeTab === 'declined' ? 'active' : ''}`}
            onClick={() => setActiveTab('declined')}
          >
            Declined
          </button>
        </div>
        
        <div className="search-container">
          <input
            type="text"
            placeholder="Search products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Requested By</th>
                <th>Quantity</th>
                <th>Current Stock</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(request => (
                <tr key={request.id}>
                  <td>{request.product_name}</td>
                  <td>{request.clerk_name}</td>
                  <td>{request.quantity}</td>
                  <td className={request.current_stock === 0 ? 'text-danger' : ''}>
                    {request.current_stock}
                  </td>
                  <td>
                    <span className={`badge ${
                      request.status === 'approved' ? 'success' : 
                      request.status === 'declined' ? 'danger' : 'warning'
                    }`}>
                      {request.status}
                    </span>
                  </td>
                  <td>
                    {request.status === 'pending' && (
                      <>
                        <button 
                          onClick={() => handleApprove(request.id)}
                          className="btn-sm success"
                        >
                          Approve
                        </button>
                        <button 
                          onClick={() => handleDecline(request.id)}
                          className="btn-sm danger"
                        >
                          Decline
                        </button>
                      </>
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

export default SupplyRequests;