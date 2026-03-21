import React, { useState, useEffect } from 'react';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import Footer from '../Footer/Footer';
import './clerk.css';

const ActivityLog = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/inventory/activity-logs');
        setLogs(response.data.logs || []);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="clerk-container">
      <SideBar />

      <div className="main-content">
        <NavBar />

        <div className="page-content">

          {/* ── Alerts ── */}
          {error   && <div className="alert alert-error">{error}</div>}
          {loading && <div className="loading">Loading activity logs...</div>}

          {/* ── Page Header ── */}
          <div className="dashboard-header">
            <h1 className="dashboard-title">Activity Log</h1>
            <p className="dashboard-subtitle">
              A record of all actions and events in your store.
            </p>
          </div>

          {/* ── Main Card ── */}
          <div className="card">
            {logs.length === 0 && !loading ? (
              <p className="table-empty">No activity logs available.</p>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Action</th>
                      <th>Details</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id}>
                        <td className="text-muted" style={{ whiteSpace: 'nowrap' }}>
                          {formatDate(log.created_at)}
                        </td>
                        <td style={{ fontWeight: 500 }}>{log.action_type}</td>
                        <td>{log.details}</td>
                        <td>
                          <span
                            className={`badge ${
                              log.status === 'success'
                                ? 'success'
                                : log.status === 'pending'
                                ? 'warning'
                                : 'danger'
                            }`}
                          >
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>{/* /page-content */}

        <Footer />
      </div>{/* /main-content */}
    </div>
  );
};

export default ActivityLog;