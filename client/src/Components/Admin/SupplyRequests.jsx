import React, { useState, useEffect } from 'react';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import Footer from '../Footer/Footer';
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
    status: request.status
      ? request.status.toLowerCase().replace('requeststatus.', '')
      : 'pending',
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
      const response = await api.put(
        `/api/inventory/supply-requests/${selectedRequestId}/decline`,
        { decline_reason: declineReason }
      );
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

        <div className="page-content">

          {/* ── Alerts ── */}
          {error && (
            <div className="alert alert-error">
              {error}
              <button className="alert-close" onClick={() => setError('')}>×</button>
            </div>
          )}
          {success && (
            <div className="alert alert-success">
              {success}
              <button className="alert-close" onClick={() => setSuccess('')}>×</button>
            </div>
          )}
          {loading && <div className="alert alert-info">Loading requests...</div>}

          {/* ── Page Header ── */}
          <div className="dashboard-header">
            <h1 className="dashboard-title">Supply Requests</h1>
            <p className="dashboard-subtitle">
              Review and manage stock replenishment requests from clerks.
            </p>
          </div>

          {/* ── Toolbar ── */}
          <div className="toolbar">
            <button
              className="button btn-ghost"
              onClick={() => fetchRequests()}
              disabled={loading}
            >
              ↻ Refresh Requests
            </button>
            <button
              className={`button ${showRawData ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setShowRawData(!showRawData)}
            >
              {showRawData ? 'Hide Raw Data' : 'Show Raw Data'}
            </button>
            <button
              className={`button ${showAllRequests ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setShowAllRequests(!showAllRequests)}
            >
              {showAllRequests ? 'Apply Filters' : 'Show All Requests'}
            </button>
          </div>

          {/* ── Raw Data Debug Panel ── */}
          {showRawData && (
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <h3 className="section-title">Raw Fetched Requests</h3>
              <pre style={{
                maxHeight: '300px',
                overflow: 'auto',
                background: 'var(--slate-50)',
                padding: '1rem',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.75rem',
                color: 'var(--slate-600)',
                border: '1px solid var(--slate-200)',
              }}>
                {JSON.stringify(requests, null, 2)}
              </pre>
            </div>
          )}

          {/* ── Main Card ── */}
          <div className="card">

            {/* ── Tabs ── */}
            <div className="tabs">
              {['pending', 'approved', 'declined'].map((tab) => (
                <button
                  key={tab}
                  className={`tab ${activeTab === tab ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            {/* ── Search ── */}
            <div className="search-container">
              <div className="search-wrapper">
                <svg
                  className="search-icon"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                <input
                  type="text"
                  placeholder="Search products..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            {/* ── Table ── */}
            {filtered.length === 0 ? (
              <p className="no-requests">
                No {activeTab} supply requests at this time.
              </p>
            ) : (
              <div className="table-wrapper">
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
                        <td style={{ fontWeight: 500 }}>
                          {request.product_name || 'Unknown Product'}
                        </td>
                        <td className="text-muted">
                          {request.clerk_name || 'Unknown Clerk'}
                        </td>
                        <td>{request.quantity || '-'}</td>
                        <td>
                          <span
                            className={`status-badge ${
                              request.current_stock <= 0 ? 'badge-danger' : 'badge-success'
                            }`}
                          >
                            {request.current_stock || 0}
                          </span>
                        </td>
                        <td>
                          <span
                            className={`status-badge ${
                              request.status === 'approved'
                                ? 'badge-success'
                                : request.status === 'declined'
                                ? 'badge-danger'
                                : 'badge-warning'
                            }`}
                          >
                            {request.status}
                          </span>
                        </td>
                        <td className="text-muted">
                          {request.decline_reason || '—'}
                        </td>
                        <td>
                          {request.status === 'pending' && (
                            <div className="action-group">
                              <button
                                onClick={() => handleApprove(request.id)}
                                className="button-action btn-action-success"
                                disabled={loading}
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedRequestId(request.id);
                                  setShowDeclineModal(true);
                                }}
                                className="button-action btn-action-danger"
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
              </div>
            )}

          </div>{/* /card */}

          {/* ── Decline Modal ── */}
          {showDeclineModal && (
            <div
              className="modal-overlay"
              onClick={(e) => e.target === e.currentTarget && setShowDeclineModal(false)}
            >
              <div className="modal-content">
                <h3 className="modal-title">Decline Supply Request</h3>

                <div className="form-group">
                  <label className="form-label">Reason for Decline</label>
                  <textarea
                    value={declineReason}
                    onChange={(e) => setDeclineReason(e.target.value)}
                    placeholder="Enter reason for declining the request..."
                    rows={4}
                  />
                </div>

                <div className="modal-actions">
                  <button
                    className="button btn-ghost"
                    onClick={() => {
                      setShowDeclineModal(false);
                      setDeclineReason('');
                      setSelectedRequestId(null);
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    className="button btn-primary"
                    onClick={handleDecline}
                    disabled={loading || !declineReason.trim()}
                  >
                    {loading ? 'Submitting...' : 'Submit'}
                  </button>
                </div>

              </div>
            </div>
          )}

        </div>{/* /page-content */}

        <Footer />
      </div>{/* /main-content */}
    </div>
  );
};

export default SupplyRequests;