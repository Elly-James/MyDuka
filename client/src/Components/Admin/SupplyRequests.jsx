import React, { useState, useEffect } from 'react';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import useSocket from '../hooks/useSocket';
import './admin.css';

const SupplyRequests = () => {
  const [requests, setRequests] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [search, setSearch] = useState('');
  const [declineReason, setDeclineReason] = useState('');
  const [showDeclineModal, setShowDeclineModal] = useState(false);
  const [selectedRequestId, setSelectedRequestId] = useState(null);
  const [showRawData, setShowRawData] = useState(false);
  const [showAllRequests, setShowAllRequests] = useState(false);
  const { socket } = useSocket();

  const normalizeRequest = (request) => ({
    ...request,
    quantity: request.quantity_requested || request.quantity || 0,
    status: request.status ? request.status.toLowerCase().replace('requeststatus.', '') : 'pending',
  });

  const fetchRequests = async (retryCount = 0, maxRetries = 5) => {
    try {
      setLoading(true);
      const response = await api.get('/api/inventory/supply-requests');
      const fetchedRequests = (response.data.requests || []).map(normalizeRequest);
      console.log('Fetched and normalized supply requests:', JSON.stringify(fetchedRequests, null, 2));
      if (fetchedRequests.length === 0) {
        console.warn('No supply requests returned from API');
      }
      setRequests(fetchedRequests);
      filterRequests(fetchedRequests);
    } catch (err) {
      if (retryCount < maxRetries) {
        console.warn(`Retrying fetch requests (${retryCount + 1}/${maxRetries})...`);
        setTimeout(() => fetchRequests(retryCount + 1, maxRetries), 1000);
      } else {
        console.error('Failed to fetch supply requests:', err);
        handleApiError(err, setError);
        const mockRequests = [
          {
            id: 427,
            product_id: 2,
            product_name: 'Sugar 2kg',
            quantity: 80,
            quantity_requested: 80,
            clerk_id: 8,
            clerk_name: 'David Davis',
            store_id: 1,
            current_stock: 70,
            status: 'pending',
            decline_reason: null,
          },
        ];
        console.log('Using mock requests:', JSON.stringify(mockRequests, null, 2));
        setRequests(mockRequests);
        filterRequests(mockRequests);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  // Listen for new supply requests via WebSocket
  useEffect(() => {
    if (!socket) {
      console.warn('Socket not initialized');
      return;
    }

    const handleNewRequest = (data) => {
      console.log('New supply request received via WebSocket:', JSON.stringify(data, null, 2));
      const newRequest = normalizeRequest({
        id: data.request_id,
        product_id: data.product_id,
        product_name: data.product_name || 'Unknown Product',
        quantity_requested: data.quantity || 0,
        clerk_id: data.clerk_id,
        clerk_name: data.clerk_name || 'Unknown Clerk',
        store_id: data.store_id,
        current_stock: data.current_stock || 0,
        status: 'PENDING',
        decline_reason: null,
      });
      setRequests((prev) => {
        const updated = [newRequest, ...prev.filter((req) => req.id !== newRequest.id)];
        console.log('Updated requests after WebSocket:', JSON.stringify(updated, null, 2));
        filterRequests(updated);
        return [...updated];
      });
    };

    socket.on('supply_request', handleNewRequest);

    return () => {
      socket.off('supply_request', handleNewRequest);
    };
  }, [socket]);

  // Filter requests based on tab and search
  const filterRequests = (reqs = requests) => {
    let filteredList = reqs;
    if (!showAllRequests) {
      filteredList = reqs.filter((request) => {
        const status = request.status || 'pending';
        const matchesTab = status === activeTab;
        const matchesSearch = request.product_name
          ? request.product_name.toLowerCase().includes(search.trim().toLowerCase())
          : true;
        return matchesTab && matchesSearch;
      });
    }
    console.log('Filtered requests:', JSON.stringify(filteredList, null, 2));
    setFiltered([...filteredList]);
  };

  useEffect(() => {
    filterRequests();
  }, [activeTab, search, requests, showAllRequests]);

  const handleApprove = async (requestId) => {
    try {
      setLoading(true);
      await api.put(`/api/inventory/supply-requests/${requestId}/approve`);
      setSuccess('Supply request approved successfully');
      setTimeout(() => setSuccess(''), 5000);
      const updatedRequests = requests.map((req) =>
        req.id === requestId ? { ...req, status: 'approved', decline_reason: null } : req
      );
      setRequests([...updatedRequests]);
      filterRequests(updatedRequests);

      // Emit WebSocket event to notify clerk
      const request = requests.find((req) => req.id === requestId);
      if (socket) {
        socket.emit('supply_request_status', {
          request_id: requestId,
          product_name: request.product_name,
          status: 'APPROVED',
          clerk_id: request.clerk_id,
        });
      }
    } catch (err) {
      handleApiError(err, setError);
    } finally {
      setLoading(false);
    }
  };

  const handleDecline = async () => {
    if (!declineReason.trim()) {
      setError('Please provide a reason for declining');
      return;
    }
    try {
      setLoading(true);
      console.log(`Declining request ID ${selectedRequestId} with reason: ${declineReason}`);
      const response = await api.put(`/api/inventory/supply-requests/${selectedRequestId}/decline`, {
        decline_reason: declineReason,
      });
      console.log('Decline response:', JSON.stringify(response.data, null, 2));
      setSuccess('Supply request declined successfully');
      setTimeout(() => setSuccess(''), 5000);
      const updatedRequests = requests.map((req) =>
        req.id === selectedRequestId
          ? { ...req, status: 'declined', decline_reason: declineReason }
          : req
      );
      setRequests([...updatedRequests]);
      filterRequests(updatedRequests);

      // Emit WebSocket event to notify clerk
      const request = requests.find((req) => req.id === selectedRequestId);
      if (socket) {
        socket.emit('supply_request_status', {
          request_id: selectedRequestId,
          product_name: request.product_name,
          status: 'DECLINED',
          decline_reason: declineReason,
          clerk_id: request.clerk_id,
        });
      }
      setShowDeclineModal(false);
      setDeclineReason('');
      setSelectedRequestId(null);
    } catch (err) {
      console.error('Decline error:', err.response?.data || err.message);
      if (err.response?.status === 403) {
        setError('Unauthorized: Please log in as an admin to decline requests');
      } else {
        handleApiError(err, setError);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-container">
      <SideBar />
      <div className="main-content">
        <NavBar />
        {error && (
          <div className="alert error" role="alert">
            {error}
            <button onClick={() => setError('')} className="alert-close">×</button>
          </div>
        )}
        {success && (
          <div className="alert success" role="alert">
            {success}
            <button onClick={() => setSuccess('')} className="alert-close">×</button>
          </div>
        )}
        {loading && <div className="loading">Loading requests...</div>}

        <h1>Supply Requests</h1>
        <div style={{ marginBottom: '20px' }}>
          <button
            onClick={() => fetchRequests()}
            className="btn-primary"
            disabled={loading}
          >
            Refresh Requests
          </button>
          <button
            onClick={() => setShowRawData(!showRawData)}
            className="btn-secondary"
            style={{ marginLeft: '10px' }}
          >
            {showRawData ? 'Hide Raw Data' : 'Show Raw Data'}
          </button>
          <button
            onClick={() => setShowAllRequests(!showAllRequests)}
            className="btn-secondary"
            style={{ marginLeft: '10px' }}
          >
            {showAllRequests ? 'Apply Filters' : 'Show All Requests'}
          </button>
        </div>

        {showRawData && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3>Raw Fetched Requests</h3>
            <pre style={{ maxHeight: '300px', overflow: 'auto' }}>
              {JSON.stringify(requests, null, 2)}
            </pre>
          </div>
        )}

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
          {filtered.length === 0 ? (
            <p className="no-requests">No {activeTab} supply requests at this time.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Requested By</th>
                  <th>Quantity</th>
                  <th>Current Stock</th>
                  <th>Status</th>
                  <th>Decline Reason</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((request) => (
                  <tr key={request.id}>
                    <td>{request.product_name || 'Unknown Product'}</td>
                    <td>{request.clerk_name || 'Unknown Clerk'}</td>
                    <td>{request.quantity || '-'}</td>
                    <td className={request.current_stock <= 0 ? 'text-danger' : ''}>
                      {request.current_stock || 0}
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          request.status === 'approved'
                            ? 'success'
                            : request.status === 'declined'
                            ? 'danger'
                            : 'warning'
                        }`}
                      >
                        {request.status}
                      </span>
                    </td>
                    <td>{request.decline_reason || '-'}</td>
                    <td>
                      {request.status === 'pending' && (
                        <div className="action-buttons">
                          <button
                            onClick={() => handleApprove(request.id)}
                            className="btn-sm success"
                            disabled={loading}
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => {
                              setSelectedRequestId(request.id);
                              setShowDeclineModal(true);
                            }}
                            className="btn-sm danger"
                            disabled={loading}
                          >
                            Decline
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {showDeclineModal && (
          <div className="modal">
            <div className="modal-content">
              <h2>Decline Supply Request</h2>
              <div className="form-group">
                <label>Reason for Decline</label>
                <textarea
                  value={declineReason}
                  onChange={(e) => setDeclineReason(e.target.value)}
                  placeholder="Enter reason for declining the request"
                  rows="4"
                />
              </div>
              <div className="modal-actions">
                <button
                  onClick={handleDecline}
                  className="btn-primary"
                  disabled={loading || !declineReason.trim()}
                >
                  Submit
                </button>
                <button
                  onClick={() => {
                    setShowDeclineModal(false);
                    setDeclineReason('');
                    setSelectedRequestId(null);
                  }}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SupplyRequests;