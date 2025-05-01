import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import './merchant.css';

const AdminManagement = () => {
  const [admins, setAdmins] = useState([]);
  const [stores, setStores] = useState([]);
  const [inviteForm, setInviteForm] = useState({ email: '', store_id: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const adminsResponse = await api.get('/api/users?role=ADMIN');
        setAdmins(adminsResponse.data.users || []);

        const storesResponse = await api.get('/api/stores');
        setStores(storesResponse.data.stores || []);
      } catch (err) {
        handleApiError(err, setError);
      }
    };
    fetchData();
  }, []);

  const handleInvite = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/auth/invite', {
        email: inviteForm.email,
        role: 'ADMIN',
        store_id: parseInt(inviteForm.store_id),
      });
      setInviteForm({ email: '', store_id: '' });
      const adminsResponse = await api.get('/api/users?role=ADMIN');
      setAdmins(adminsResponse.data.users || []);
      setError('');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this admin?')) {
      try {
        await api.delete(`/api/users/${id}`);
        setAdmins(admins.filter(admin => admin.id !== id));
      } catch (err) {
        handleApiError(err, setError);
      }
    }
  };

  const handleDeactivate = async (id) => {
    try {
      await api.put(`/api/users/${id}/status`, { status: 'inactive' });
      setAdmins(admins.map(admin => admin.id === id ? { ...admin, status: 'inactive' } : admin));
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handleActivate = async (id) => {
    try {
      await api.put(`/api/users/${id}/status`, { status: 'active' });
      setAdmins(admins.map(admin => admin.id === id ? { ...admin, status: 'active' } : admin));
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
          <h2 className="card-title">Invite New Admin</h2>
          <form onSubmit={handleInvite} className="space-y-4">
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
              <label>Store</label>
              <select
                value={inviteForm.store_id}
                onChange={(e) => setInviteForm({ ...inviteForm, store_id: e.target.value })}
                required
              >
                <option value="">Select a store</option>
                {stores.map(store => (
                  <option key={store.id} value={store.id}>{store.name}</option>
                ))}
              </select>
            </div>
            <button type="submit" className="button button-primary">
              Invite Admin
            </button>
          </form>
        </div>

        <div className="card">
          <h2 className="card-title">Existing Admins</h2>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {admins.map(admin => (
                <tr key={admin.id}>
                  <td>{admin.name}</td>
                  <td>{admin.email}</td>
                  <td>
                    <span className={`status-badge ${admin.status === 'active' ? 'status-active' : 'status-inactive'}`}>
                      {admin.status}
                    </span>
                  </td>
                  <td className="space-x-2">
                    {admin.status === 'active' ? (
                      <button onClick={() => handleDeactivate(admin.id)} className="button-action">Deactivate</button>
                    ) : (
                      <button onClick={() => handleActivate(admin.id)} className="button-action">Activate</button>
                    )}
                    <button onClick={() => handleDelete(admin.id)} className="button-action text-red-600">Delete</button>
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

export default AdminManagement;