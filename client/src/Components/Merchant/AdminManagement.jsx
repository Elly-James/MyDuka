import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../utils/api';
import './merchant.css';

const AdminManage = () => {
  const [admins, setAdmins] = useState([]);
  const [inviteForm, setInviteForm] = useState({ email: '', store_id: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchAdmins();
  }, []);

  const fetchAdmins = async () => {
    try {
      const response = await api.get('/api/users?role=ADMIN');
      setAdmins(response.data.users || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to fetch admins');
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/auth/invite', {
        email: inviteForm.email,
        role: 'ADMIN',
        store_id: parseInt(inviteForm.store_id),
      });
      setInviteForm({ email: '', store_id: '' });
      fetchAdmins();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to send invitation');
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this admin?')) {
      try {
        await api.delete(`/api/users/${id}`);
        fetchAdmins();
      } catch (err) {
        setError(err.response?.data?.message || 'Failed to delete admin');
      }
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
        <div className="admin-manage">
          <h1>Admin Management</h1>
          <h2>Invite New Admin</h2>
          <form onSubmit={handleInvite}>
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={inviteForm.email}
                onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Store ID</label>
              <input
                type="number"
                value={inviteForm.store_id}
                onChange={(e) => setInviteForm({ ...inviteForm, store_id: e.target.value })}
                required
              />
            </div>
            <button type="submit">Invite Admin</button>
          </form>
          {error && <p className="error">{error}</p>}
          <h2>Existing Admins</h2>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Store ID</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {admins.map((admin) => (
                <tr key={admin.id}>
                  <td>{admin.name}</td>
                  <td>{admin.email}</td>
                  <td>{admin.store_id}</td>
                  <td>
                    <button className="delete" onClick={() => handleDelete(admin.id)}>Delete</button>
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

export default AdminManage;