import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import './admin.css';

const SupplyRequests = () => {
  const [requests, setRequests] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [loading, setLoading] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);
  
  const { token } = useAuth();

  useEffect(() => {
    fetchSupplyRequests();
  }, [activeTab]);

  const fetchSupplyRequests = async () => {
    setLoading(true);
    try {
      // In a real implementation, you would call your API endpoint
      // const response = await axios.get(`/api/inventory/supply-requests?status=${activeTab}`, {
      //   headers: { Authorization: `Bearer ${token}` }
      // });
      
      // For demonstration, using mock data similar to the image
      const mockData = {
        data: [
          { 
            id: 1, 
            product: 'Rice (5kg bags)', 
            clerk: 'Jane Smith',
            quantity: 50,
            currentStock: 5,
            requestDate: '2025-04-22',
            status: 'pending'
          },
          { 
            id: 2, 
            product: 'Cooking Oil (2L)', 
            clerk: 'John Doe',
            quantity: 30,
            currentStock: 2,
            requestDate: '2025-04-21',
            status: 'pending'
          },
          { 
            id: 3, 
            product: 'Sugar (1kg packs)', 
            clerk: 'Sarah Johnson',
            quantity: 25,
            currentStock: 0,
            requestDate: '2025-04-20',
            status: 'pending'
          },
          // Add more mock data for approved and declined tabs if needed
        ],
        meta: {
          pendingCount: 3
        }
      };

      // Filter based on activeTab
      const filteredData = mockData.data.filter(request => request.status === activeTab);

      setRequests(filteredData);
      setPendingCount(mockData.meta.pendingCount);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching supply requests:', error);
      setLoading(false);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  const handleApprove = async (id) => {
    try {
      // In real implementation, you would call your API
      // await axios.put(`/api/inventory/supply-requests/${id}/approve`, {}, {
      //   headers: { Authorization: `Bearer ${token}` }
      // });
      
      // For demonstration, update the local state
      const updatedRequests = requests.filter(request => request.id !== id);
      setRequests(updatedRequests);
      setPendingCount(prev => prev - 1);
    } catch (error) {
      console.error('Error approving supply request:', error);
    }
  };

  const handleDecline = async (id) => {
    try {
      // In real implementation, you would call your API
      // await axios.put(`/api/inventory/supply-requests/${id}/decline`, {}, {
      //   headers: { Authorization: `Bearer ${token}` }
      // });
      
      // For demonstration, update the local state
      const updatedRequests = requests.filter(request => request.id !== id);
      setRequests(updatedRequests);
      setPendingCount(prev => prev - 1);
    } catch (error) {
      console.error('Error declining supply request:', error);
    }
  };

  return (
    <div className="supply-requests-container">
      <h1 className="page-title">Supply Requests</h1>
      
      <div className="tabs-container">
        <button 
          className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => handleTabChange('pending')}
        >
          Pending
        </button>
        <button 
          className={`tab ${activeTab === 'approved' ? 'active' : ''}`}
          onClick={() => handleTabChange('approved')}
        >
          Approved
        </button>
        <button 
          className={`tab ${activeTab === 'declined' ? 'active' : ''}`}
          onClick={() => handleTabChange('declined')}
        >
          Declined
        </button>
      </div>
      
      {loading ? (
        <p className="loading">Loading supply requests...</p>
      ) : (
        <>
          <table className="supply-requests-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Clerk</th>
                <th>Quantity</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.id}>
                  <td className="product-cell">
                    <div>{request.product}</div>
                    <div className="request-date">Request date: {new Date(request.requestDate).toLocaleDateString('en-US', { month: 'short', day: '2-digit' })}</div>
                  </td>
                  <td>{request.clerk}</td>
                  <td className="quantity-cell">
                    <div>{request.quantity} units</div>
                    <div className={`current-stock ${request.currentStock === 0 ? 'out-of-stock' : 'low-stock'}`}>
                      Current stock: {request.currentStock}
                    </div>
                  </td>
                  <td className="actions-cell">
                    <div className="action-buttons">
                      <button 
                        className="decline-button"
                        onClick={() => handleDecline(request.id)}
                      >
                        Decline
                      </button>
                      <button 
                        className="approve-button"
                        onClick={() => handleApprove(request.id)}
                      >
                        Approve
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {requests.length === 0 && (
                <tr>
                  <td colSpan="4" className="no-data">
                    No {activeTab} supply requests found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          
          {activeTab === 'pending' && pendingCount > 0 && (
            <div className="notification-banner">
              <span className="notification-icon">⚠</span>
              <span>{pendingCount} pending supply requests require your attention</span>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default SupplyRequests;