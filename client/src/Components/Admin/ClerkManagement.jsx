import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api, handleApiError } from '../utils/api';
import useSocket from '../hooks/useSocket';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import Footer from '../Footer/Footer';
import { FaEdit, FaTrash } from 'react-icons/fa';
import debounce from 'lodash/debounce';
import './admin.css';

const ClerkManagement = () => {
  const [clerks, setClerks] = useState([]);
  const [stores, setStores] = useState([]);
  const [inviteForm, setInviteForm] = useState({ name: '', email: '', store_id: '' });
  const [editForm, setEditForm] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const clerksPerPage = 10;

  const { socket } = useSocket();

  const fetchClerks = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get(
        `/api/users/clerks?search=${encodeURIComponent(searchTerm)}&page=${currentPage}&per_page=${clerksPerPage}`
      );
      setClerks(response.data.clerks || []);
      setTotalPages(response.data.pages || 1);
    } catch (err) {
      handleApiError(err, setError);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm]);

  const fetchStores = useCallback(async () => {
    try {
      const response = await api.get('/api/stores');
      setStores(response.data.stores || []);
    } catch (err) {
      handleApiError(err, setError);
    }
  }, []);

  const fetchData = useCallback(async () => {
    await Promise.all([fetchClerks(), fetchStores()]);
  }, [fetchClerks, fetchStores]);

  const debouncedSearch = useMemo(
    () => debounce((value) => {
      setSearchTerm(value);
      setCurrentPage(1);
    }, 300),
    []
  );

  useEffect(() => {
    fetchData();

    if (socket) {
      socket.on('user_updated', (updatedUser) => {
        if (updatedUser.role === 'CLERK') {
          setClerks((prev) =>
            prev.map((clerk) =>
              clerk.id === updatedUser.id
                ? { ...clerk, ...updatedUser, stores: updatedUser.stores || clerk.stores }
                : clerk
            )
          );
          setSuccess('Clerk updated successfully');
          setTimeout(() => setSuccess(''), 4000);
        }
      });
      socket.on('user_deleted', ({ id }) => {
        setClerks((prev) => prev.filter((clerk) => clerk.id !== id));
        setSuccess('Clerk deleted successfully');
        setTimeout(() => setSuccess(''), 4000);
      });
      socket.on('user_invited', (invitedUser) => {
        if (invitedUser.role === 'CLERK') {
          setSuccess(`Invitation sent to ${invitedUser.email}`);
          setTimeout(() => setSuccess(''), 4000);
        }
      });
      socket.on('user_created', (newUser) => {
        if (newUser.role === 'CLERK') {
          setClerks((prev) => [newUser, ...prev]);
          setSuccess(`New clerk ${newUser.email} has registered`);
          setTimeout(() => setSuccess(''), 4000);
        }
      });
      socket.on('new_notification', (notification) => {
        if (['USER_INVITED', 'ACCOUNT_STATUS', 'ACCOUNT_DELETION'].includes(notification.type)) {
          setSuccess(notification.message);
          setTimeout(() => setSuccess(''), 4000);
        }
      });
    }

    return () => {
      if (socket) {
        socket.off('user_updated');
        socket.off('user_deleted');
        socket.off('user_invited');
        socket.off('user_created');
        socket.off('new_notification');
      }
    };
  }, [fetchData, socket]);

  const handleInvite = async (e) => {
    e.preventDefault();
    setActionLoading((prev) => ({ ...prev, invite: true }));
    setError(''); setSuccess('');
    try {
      await api.post('/api/auth/invite', {
        name: inviteForm.name.trim(),
        email: inviteForm.email.trim().toLowerCase(),
        role: 'CLERK',
        store_id: parseInt(inviteForm.store_id),
      });
      setInviteForm({ name: '', email: '', store_id: '' });
      setShowInviteModal(false);
      setSuccess('Invitation sent successfully');
      setTimeout(() => setSuccess(''), 4000);
      fetchClerks();
    } catch (err) {
      handleApiError(err, setError);
    } finally {
      setActionLoading((prev) => ({ ...prev, invite: false }));
    }
  };

  const handleEdit = (clerk) => {
    setEditForm({
      id: clerk.id,
      name: clerk.name,
      email: clerk.email,
      store_ids: clerk.stores.map((store) => store.id),
    });
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setActionLoading((prev) => ({ ...prev, [editForm.id]: true }));
    setError(''); setSuccess('');
    try {
      const response = await api.put(`/api/users/${editForm.id}`, {
        name: editForm.name.trim(),
        email: editForm.email.trim().toLowerCase(),
        store_ids: editForm.store_ids,
      });
      const updatedUser = response.data.user;
      setClerks((prev) =>
        prev.map((clerk) =>
          clerk.id === updatedUser.id
            ? { ...clerk, ...updatedUser, stores: updatedUser.stores || clerk.stores }
            : clerk
        )
      );
      setEditForm(null);
      setSuccess('Clerk updated successfully');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      handleApiError(err, setError);
    } finally {
      setActionLoading((prev) => ({ ...prev, [editForm.id]: false }));
    }
  };

  const handleStatusToggle = async (id, currentStatus) => {
    const newStatus = currentStatus === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    setActionLoading((prev) => ({ ...prev, [id]: true }));
    setError(''); setSuccess('');
    try {
      const response = await api.put(`/api/users/${id}/status`, { status: newStatus });
      const updatedUser = response.data.user;
      setClerks((prev) =>
        prev.map((clerk) =>
          clerk.id === updatedUser.id
            ? { ...clerk, ...updatedUser, stores: updatedUser.stores || clerk.stores }
            : clerk
        )
      );
      setSuccess(`Clerk status updated to ${newStatus.toLowerCase()}`);
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      handleApiError(err, setError);
    } finally {
      setActionLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this clerk?')) {
      setActionLoading((prev) => ({ ...prev, [id]: true }));
      setError(''); setSuccess('');
      try {
        await api.delete(`/api/users/${id}`);
        setClerks((prev) => prev.filter((clerk) => clerk.id !== id));
        setSuccess('Clerk deleted successfully');
        setTimeout(() => setSuccess(''), 4000);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setActionLoading((prev) => ({ ...prev, [id]: false }));
      }
    }
  };

  const paginate = (pageNumber) => {
    if (pageNumber >= 1 && pageNumber <= totalPages) setCurrentPage(pageNumber);
  };

  return (
    <div className="admin-container">
      <SideBar />

      <div className="main-content">
        <NavBar />

        <div className="page-content">

          {/* ── Alerts ── */}
          {error   && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}
          {loading && <div className="alert alert-info">Loading...</div>}

          {/* ── Page Header ── */}
          <div className="dashboard-header">
            <h1 className="dashboard-title">Clerk Management</h1>
            <p className="dashboard-subtitle">Manage your store clerks and their access.</p>
          </div>

          {/* ── Main Card ── */}
          <div className="card">

            {/* Card header */}
            <div className="card-header">
              <h2 className="card-title">Clerks</h2>
              <div className="toolbar" style={{ margin: 0 }}>
                <div className="search-wrapper">
                  <svg className="search-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <input
                    type="text"
                    placeholder="Search clerks by name, email, or store..."
                    onChange={(e) => debouncedSearch(e.target.value)}
                  />
                </div>
                <button onClick={() => setShowInviteModal(true)} className="button btn-primary">
                  + Invite Clerk
                </button>
              </div>
            </div>

            {/* ── Invite Modal ── */}
            {showInviteModal && (
              <div
                className="modal-overlay"
                onClick={(e) => e.target === e.currentTarget && setShowInviteModal(false)}
              >
                <div className="modal-content">
                  <h3 className="modal-title">Invite New Clerk</h3>
                  <form onSubmit={handleInvite}>
                    <div className="form-group">
                      <label htmlFor="invite-name" className="form-label">Name</label>
                      <input
                        type="text"
                        id="invite-name"
                        value={inviteForm.name}
                        onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })}
                        placeholder="Enter clerk name"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="invite-email" className="form-label">Email</label>
                      <input
                        type="email"
                        id="invite-email"
                        value={inviteForm.email}
                        onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                        placeholder="Enter clerk email"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="invite-store" className="form-label">Store</label>
                      <select
                        id="invite-store"
                        value={inviteForm.store_id}
                        onChange={(e) => setInviteForm({ ...inviteForm, store_id: e.target.value })}
                        required
                      >
                        <option value="">Select a store</option>
                        {stores.map((store) => (
                          <option key={store.id} value={store.id}>{store.name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="modal-actions">
                      <button
                        type="button"
                        className="button btn-ghost"
                        onClick={() => { setInviteForm({ name: '', email: '', store_id: '' }); setShowInviteModal(false); }}
                      >
                        Cancel
                      </button>
                      <button type="submit" className="button btn-primary" disabled={actionLoading.invite}>
                        {actionLoading.invite ? 'Sending...' : 'Send Invite'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* ── Table ── */}
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Stores</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {clerks.length > 0 ? (
                    clerks.map((clerk) => (
                      <tr key={clerk.id}>
                        <td>
                          {editForm && editForm.id === clerk.id ? (
                            <input
                              type="text"
                              value={editForm.name}
                              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                              required
                            />
                          ) : (
                            <span style={{ fontWeight: 500 }}>{clerk.name}</span>
                          )}
                        </td>
                        <td>
                          {editForm && editForm.id === clerk.id ? (
                            <input
                              type="email"
                              value={editForm.email}
                              onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                              required
                            />
                          ) : (
                            <span className="text-muted">{clerk.email}</span>
                          )}
                        </td>
                        <td>
                          {editForm && editForm.id === clerk.id ? (
                            <select
                              multiple
                              value={editForm.store_ids}
                              onChange={(e) =>
                                setEditForm({
                                  ...editForm,
                                  store_ids: Array.from(e.target.selectedOptions, (o) => parseInt(o.value)),
                                })
                              }
                            >
                              {stores.map((store) => (
                                <option key={store.id} value={store.id}>{store.name}</option>
                              ))}
                            </select>
                          ) : (
                            <span className="text-muted">
                              {clerk.stores?.map((s) => s.name).join(', ') || 'N/A'}
                            </span>
                          )}
                        </td>
                        <td>
                          <span className={`status-badge ${clerk.status === 'ACTIVE' ? 'badge-success' : 'badge-danger'}`}>
                            {clerk.status}
                          </span>
                        </td>
                        <td>
                          <div className="action-group">
                            {editForm && editForm.id === clerk.id ? (
                              <>
                                <button
                                  onClick={handleEditSubmit}
                                  className="button-action btn-action-success"
                                  disabled={actionLoading[clerk.id]}
                                >
                                  {actionLoading[clerk.id] ? 'Saving...' : 'Save'}
                                </button>
                                <button onClick={() => setEditForm(null)} className="button-action btn-action-ghost">
                                  Cancel
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => handleStatusToggle(clerk.id, clerk.status)}
                                  className={`button-action ${clerk.status === 'ACTIVE' ? 'btn-action-warning' : 'btn-action-success'}`}
                                  disabled={actionLoading[clerk.id]}
                                >
                                  {actionLoading[clerk.id] ? '...' : clerk.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
                                </button>
                                <button
                                  onClick={() => handleEdit(clerk)}
                                  className="button-action btn-action-primary"
                                  disabled={actionLoading[clerk.id]}
                                  title="Edit Clerk"
                                >
                                  {actionLoading[clerk.id] ? '...' : '✏️'}
                                </button>
                                <button
                                  onClick={() => handleDelete(clerk.id)}
                                  className="button-action btn-action-danger"
                                  disabled={actionLoading[clerk.id]}
                                  title="Delete Clerk"
                                >
                                  {actionLoading[clerk.id] ? '...' : '🗑️'}
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="5" className="table-empty">No clerks found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* ── Pagination ── */}
            <div className="card-footer-row">
              <div className="pagination">
                <button
                  className="pagination-button"
                  onClick={() => paginate(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  ← Previous
                </button>
                {Array.from({ length: totalPages }, (_, i) => (
                  <button
                    key={i + 1}
                    className={`pagination-button ${currentPage === i + 1 ? 'pagination-active' : ''}`}
                    onClick={() => paginate(i + 1)}
                  >
                    {i + 1}
                  </button>
                ))}
                <button
                  className="pagination-button"
                  onClick={() => paginate(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Next →
                </button>
              </div>
            </div>

          </div>{/* /card */}
        </div>{/* /page-content */}

        <Footer />
      </div>{/* /main-content */}
    </div>
  );
};

export default React.memo(ClerkManagement);