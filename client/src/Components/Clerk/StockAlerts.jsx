
import React, { useState, useEffect, useContext } from 'react';
import { api, handleApiError } from '../utils/api';
import { AuthContext } from '../context/AuthContext';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import useSocket from '../hooks/useSocket';
import './clerk.css';

const StockAlerts = () => {
  const { user } = useContext(AuthContext);
  const [alerts, setAlerts] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const { socket } = useSocket();
  const [requestQuantities, setRequestQuantities] = useState({});

  // Normalize status to remove 'RequestStatus.' prefix
  const normalizeStatus = (status) => {
    if (!status) return 'PENDING';
    return status.replace(/^RequestStatus\./, '').toUpperCase();
  };

  // Normalize request data to ensure consistent field names
  const normalizeRequest = (request) => ({
    ...request,
    status: normalizeStatus(request.status),
    quantity: request.quantity_requested || request.quantity || 0,
  });

  // Fetch low stock alerts
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/inventory/low-stock');
        const alertsData = response.data?.alerts || [];
        setAlerts(Array.isArray(alertsData) ? alertsData : []);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  // Fetch supply requests made by the clerk
  useEffect(() => {
    const fetchRequests = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/inventory/supply-requests');
        const normalizedRequests = (response.data.requests || []).map(normalizeRequest);
        setRequests(normalizedRequests);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchRequests();
  }, []);

  // Listen for supply request status updates via WebSocket
  useEffect(() => {
    if (!socket) return;

    const handleStatusUpdate = (data) => {
      setRequests((prevRequests) =>
        prevRequests.map((req) =>
          req.id === data.request_id
            ? normalizeRequest({
                ...req,
                status: data.status,
                decline_reason: data.decline_reason || null,
                quantity: req.quantity, // Preserve existing quantity
              })
            : req
        )
      );
      setSuccess(`Supply request for ${data.product_name} has been ${normalizeStatus(data.status)}`);
      setTimeout(() => setSuccess(''), 5000);
    };

    socket.on('supply_request_status', handleStatusUpdate);

    return () => {
      socket.off('supply_request_status', handleStatusUpdate);
    };
  }, [socket]);

  const handleQuantityChange = (productId, value) => {
    setRequestQuantities((prev) => ({
      ...prev,
      [productId]: value,
    }));
  };

  const handleRequestSupply = async (productId, productName) => {
    const quantity = parseInt(requestQuantities[productId], 10) || 10;
    if (quantity <= 0) {
      setError('Please enter a valid quantity greater than 0');
      return;
    }

    if (!user?.store?.id || !user?.id) {
      setError('User or store information is missing. Please log in again.');
      return;
    }

    try {
      setLoading(true);
      const payload = {
        product_id: productId,
        quantity_requested: quantity,
        store_id: user.store.id,
        clerk_id: user.id,
        status: 'PENDING',
      };
      const response = await api.post('/api/inventory/supply-requests', payload);
      setSuccess('Supply request submitted successfully');
      setTimeout(() => setSuccess(''), 5000);

      setAlerts(alerts.filter((a) => a.product_id !== productId));
      setRequestQuantities((prev) => {
        const updated = { ...prev };
        delete updated[productId];
        return updated;
      });

      const newRequest = normalizeRequest({
        id: response.data.request.id,
        product_id: productId,
        product_name: productName,
        quantity_requested: quantity, // Use quantity_requested for consistency
        status: 'PENDING',
        decline_reason: null,
      });
      setRequests((prev) => [newRequest, ...prev]);

      if (socket) {
        socket.emit('supply_request', {
          request_id: response.data.request.id,
          product_id: productId,
          product_name: productName,
          quantity,
          message: `New supply request for ${productName}: ${quantity} units`,
          type: 'SUPPLY_REQUEST',
          clerk_id: user.id,
          clerk_name: user.name,
          store_id: user.store.id,
        });
      }
    } catch (err) {
      const errorMessage = err.response?.data?.errors
        ? Object.values(err.response.data.errors).flat().join(' ')
        : 'Failed to submit supply request. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="clerk-container">
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
        {loading && <div className="loading">Loading stock alerts...</div>}
        <h1>Stock Alerts</h1>
        <div className="card">
          {!loading && alerts.length === 0 ? (
            <p className="no-alerts">No low stock items at this time.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Current Stock</th>
                  <th>Minimum Required</th>
                  <th>Quantity to Request</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert) => (
                  <tr key={alert.product_id}>
                    <td>{alert.product_name}</td>
                    <td
                      className={
                        alert.current_stock <= alert.min_stock_level
                          ? 'text-danger'
                          : ''
                      }
                    >
                      {alert.current_stock}
                    </td>
                    <td>{alert.min_stock_level}</td>
                    <td>
                      <input
                        type="number"
                        min="1"
                        value={requestQuantities[alert.product_id] || ''}
                        onChange={(e) =>
                          handleQuantityChange(alert.product_id, e.target.value)
                        }
                        placeholder="Enter quantity"
                        className="quantity-input"
                      />
                    </td>
                    <td>
                      <button
                        onClick={() =>
                          handleRequestSupply(alert.product_id, alert.product_name)
                        }
                        className="btn-primary"
                        disabled={loading}
                      >
                        {loading ? 'Processing...' : 'Request Supply'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <h2>Supply Requests History</h2>
        <div className="card">
          {requests.length === 0 ? (
            <p>No supply requests submitted yet.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Quantity Requested</th>
                  <th>Status</th>
                  <th>Decline Reason</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr key={request.id}>
                    <td>{request.product_name}</td>
                    <td>{request.quantity}</td>
                    <td>
                      <span
                        className={`badge ${
                          request.status === 'APPROVED'
                            ? 'success'
                            : request.status === 'DECLINED'
                            ? 'danger'
                            : 'warning'
                        }`}
                      >
                        {request.status}
                      </span>
                    </td>
                    <td>{request.decline_reason || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default StockAlerts;
