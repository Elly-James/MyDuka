// src/Components/Clerk/ActivityLog.jsx
import React, { useState, useEffect } from 'react';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './clerk.css';

const ActivityLog = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/activity-logs');
        setLogs(response.data.logs);
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
        
        {error && <div className="alert error">{error}</div>}
        {loading && <div className="loading">Loading activity logs...</div>}

        <h1>Activity Log</h1>
        
        <div className="card">
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
                  <td>{formatDate(log.created_at)}</td>
                  <td>{log.action_type}</td>
                  <td>{log.details}</td>
                  <td>
                    <span className={`badge ${
                      log.status === 'success' ? 'success' : 
                      log.status === 'pending' ? 'warning' : 'danger'
                    }`}>
                      {log.status}
                    </span>
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

export default ActivityLog;