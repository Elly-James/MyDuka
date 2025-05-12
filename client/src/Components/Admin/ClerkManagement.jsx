import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api, handleApiError } from '../utils/api';
import useSocket from '../hooks/useSocket';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './admin.css';
import debounce from 'lodash/debounce';

const ClerkManagement = () => {
  const [clerks, setClerks] = useState([]);
  const [stores, setStores] = useState([]);
  const [inviteForm, setInviteForm] = useState({ name: '', email: '', store_ids: [] });
  const [editForm, setEditForm] = useState(null); // { id, name, email, store_ids }
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
      console.log('Clerks response:', response.data); // Debug log
      setClerks(response.data.clerks || []);
      setTotalPages(response.data.pages || 1);
    } catch (err) {
      console.error('Error fetching clerks:', err); // Debug log
      handleApiError(err, setError);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [clerksResponse, storesResponse] = await Promise.all([
        api.get(
          `/api/users/clerks?search=${encodeURIComponent(searchTerm)}&page=${currentPage}&per_page=${clerksPerPage}`
        ),
        api.get('/api/stores'),
      ]);
      console.log('Clerks response:', clerksResponse.data); // Debug log
      console.log('Stores response:', storesResponse.data); // Debug log
      setClerks(clerksResponse.data.clerks || []);
      setTotalPages(clerksResponse.data.pages || 1);
      setStores(storesResponse.data.stores || []);
    } catch (err) {
      console.error('Error fetching data:', err); // Debug log
      handleApiError(err, setError);
    } finally {
      setLoading(false);
    }
  }, [currentPage, searchTerm]);

  // Debounced search handler
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
        setClerks((prev) =>
          prev.map((clerk) =>
            clerk.id === updatedUser.id
              ? {
                  ...clerk,
                  ...updatedUser,
                  stores: updatedUser.stores || clerk.stores,
                  role: updatedUser.role,
                  status: updatedUser.status,
                }
              : clerk
          )
        );
        setSuccess('Clerk updated successfully');
        setTimeout(() => setSuccess(''), 4000);
      });

      socket.on('user_deleted', ({ id }) => {
        setClerks((prev) => prev.filter((clerk) => clerk.id !== id));
        setSuccess('Clerk deleted successfully');
        setTimeout(() => setSuccess(''), 4000);
      });

      socket.on('user_invited', (invitedUser) => {
        setSuccess(`Invitation sent to ${invitedUser.email}`);
        setTimeout(() => setSuccess(''), 4000);
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
    setError('');
    setSuccess('');
    try {
      await api.post('/api/auth/invite', {
        name: inviteForm.name.trim(),
        email: inviteForm.email.trim().toLowerCase(),
        role: 'CLERK',
        store_ids: inviteForm.store_ids.map(id => parseInt(id)),
      });
      setInviteForm({ name: '', email: '', store_ids: [] });
      setShowInviteModal(false);
      setSuccess('Invitation sent successfully');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      console.error('Error sending invite:', err); // Debug log
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
    setError('');
    setSuccess('');
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
            ? {
                ...clerk,
                ...updatedUser,
                stores: updatedUser.stores || clerk.stores,
                role: updatedUser.role,
                status: updatedUser.status,
              }
            : clerk
        )
      );
      setEditForm(null);
      setSuccess('Clerk updated successfully');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      console.error('Error updating clerk:', err); // Debug log
      handleApiError(err, setError);
    } finally {
      setActionLoading((prev) => ({ ...prev, [editForm.id]: false }));
    }
  };

  const handleStatusToggle = async (id, currentStatus) => {
    const newStatus = currentStatus === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    setActionLoading((prev) => ({ ...prev, [id]: true }));
    setError('');
    setSuccess('');
    try {
      const response = await api.put(`/api/users/${id}/status`, { status: newStatus });
      const updatedUser = response.data.user;
      setClerks((prev) =>
        prev.map((clerk) =>
          clerk.id === updatedUser.id
            ? {
                ...clerk,
                ...updatedUser,
                stores: updatedUser.stores || clerk.stores,
                role: updatedUser.role,
                status: updatedUser.status,
              }
            : clerk
        )
      );
      setSuccess(`Clerk status updated to ${newStatus.toLowerCase()}`);
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      console.error('Error toggling status:', err); // Debug log
      handleApiError(err, setError);
    } finally {
      setActionLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this clerk?')) {
      setActionLoading((prev) => ({ ...prev, [id]: true }));
      setError('');
      setSuccess('');
      try {
        await api.delete(`/api/users/${id}`);
        setClerks((prev) => prev.filter((clerk) => clerk.id !== id));
        setSuccess('Clerk deleted successfully');
        setTimeout(() => setSuccess(''), 4000);
      } catch (err) {
        console.error('Error deleting clerk:', err); // Debug log
        handleApiError(err, setError);
      } finally {
        setActionLoading((prev) => ({ ...prev, [id]: false }));
      }
    }
  };

  const paginate = (pageNumber) => {
    if (pageNumber >= 1 && pageNumber <= totalPages) {
      setCurrentPage(pageNumber);
    }
  };

  return (
    <div className="admin-container flex min-h-screen bg-gray-100">
      <SideBar />
      <div className="main-content flex-1 p-6">
        <NavBar />
        {error && (
          <p className="text-red-500 mb-4 bg-red-100 p-3 rounded">{error}</p>
        )}
        {success && (
          <p className="text-green-500 mb-4 bg-green-100 p-3 rounded">{success}</p>
        )}
        {loading && (
          <p className="text-gray-500 bg-gray-100 p-3 rounded">Loading...</p>
        )}

        <div className="card bg-white p-6 rounded-lg shadow">
          <div className="header">
            <h1 className="card-title text-2xl font-bold">Clerk Management</h1>
            <button 
              onClick={() => setShowInviteModal(true)}
              className="btn-primary px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              + Invite Clerk
            </button>
          </div>

          <div className="flex justify-between items-center mb-4 mt-4">
            <input
              type="text"
              placeholder="Search clerks by name, email, or store..."
              onChange={(e) => debouncedSearch(e.target.value)}
              className="p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {showInviteModal && (
            <div className="modal-overlay fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
              <div className="modal-content bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
                <h3 className="modal-title text-xl font-bold mb-4">Invite New Clerk</h3>
                <form onSubmit={handleInvite} className="invite-form space-y-4">
                  <div className="form-group">
                    <label htmlFor="name" className="form-label text-gray-700">
                      Name
                    </label>
                    <input
                      type="text"
                      id="name"
                      value={inviteForm.name}
                      onChange={(e) =>
                        setInviteForm({ ...inviteForm, name: e.target.value })
                      }
                      className="form-input p-2 border border-gray-300 rounded-lg w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="Enter clerk name"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="email" className="form-label text-gray-700">
                      Email
                    </label>
                    <input
                      type="email"
                      id="email"
                      value={inviteForm.email}
                      onChange={(e) =>
                        setInviteForm({ ...inviteForm, email: e.target.value })
                      }
                      className="form-input p-2 border border-gray-300 rounded-lg w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="Enter clerk email"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="store_ids" className="form-label text-gray-700">
                      Stores
                    </label>
                    <select
                      id="store_ids"
                      multiple
                      value={inviteForm.store_ids}
                      onChange={(e) =>
                        setInviteForm({
                          ...inviteForm,
                          store_ids: Array.from(
                            e.target.selectedOptions,
                            (option) => parseInt(option.value)
                          ),
                        })
                      }
                      className="form-input p-2 border border-gray-300 rounded-lg w-full max-h-40 overflow-y-auto focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      required
                    >
                      {stores.length > 0 ? (
                        stores.map((store) => (
                          <option key={store.id} value={store.id}>
                            {store.name}
                          </option>
                        ))
                      ) : (
                        <option disabled>No stores available</option>
                      )}
                    </select>
                  </div>
                  <div className="modal-actions flex gap-4">
                    <button
                      type="submit"
                      className="button px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                      disabled={actionLoading.invite}
                    >
                      {actionLoading.invite ? 'Sending...' : 'Send Invite'}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setInviteForm({ name: '', email: '', store_ids: [] });
                        setShowInviteModal(false);
                      }}
                      className="button px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          <table className="table w-full mb-6 border-collapse">
            <thead>
              <tr className="bg-gray-200">
                <th className="p-3 text-left">Name</th>
                <th className="p-3 text-left">Email</th>
                <th className="p-3 text-left">Stores</th>
                <th className="p-3 text-left">Status</th>
                <th className="p-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {clerks.length > 0 ? (
                clerks.map((clerk) => (
                  <tr key={clerk.id} className="border-b">
                    <td className="p-3">
                      {editForm && editForm.id === clerk.id ? (
                        <input
                          type="text"
                          value={editForm.name}
                          onChange={(e) =>
                            setEditForm({ ...editForm, name: e.target.value })
                          }
                          className="p-2 border border-gray-300 rounded-lg w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          required
                        />
                      ) : (
                        clerk.name
                      )}
                    </td>
                    <td className="p-3">
                      {editForm && editForm.id === clerk.id ? (
                        <input
                          type="email"
                          value={editForm.email}
                          onChange={(e) =>
                            setEditForm({ ...editForm, email: e.target.value })
                          }
                          className="p-2 border border-gray-300 rounded-lg w-full focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          required
                        />
                      ) : (
                        clerk.email
                      )}
                    </td>
                    <td className="p-3">
                      {editForm && editForm.id === clerk.id ? (
                        <select
                          multiple
                          value={editForm.store_ids}
                          onChange={(e) =>
                            setEditForm({
                              ...editForm,
                              store_ids: Array.from(
                                e.target.selectedOptions,
                                (option) => parseInt(option.value)
                              ),
                            })
                          }
                          className="p-2 border border-gray-300 rounded-lg w-full max-h-40 overflow-y-auto focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        >
                          {stores.map((store) => (
                            <option key={store.id} value={store.id}>
                              {store.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        clerk.stores?.map((store) => store.name).join(', ') || 'N/A'
                      )}
                    </td>
                    <td className="p-3">
                      <span
                        className={`status-badge px-2 py-1 rounded-full text-sm ${
                          clerk.status === 'ACTIVE'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {clerk.status}
                      </span>
                    </td>
                    <td className="p-3 space-x-2">
                      {editForm && editForm.id === clerk.id ? (
                        <>
                          <button
                            onClick={handleEditSubmit}
                            className="button-action px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700"
                            disabled={actionLoading[clerk.id]}
                          >
                            {actionLoading[clerk.id] ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            onClick={() => setEditForm(null)}
                            className="button-action px-3 py-1 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => handleEdit(clerk)}
                            className="button-action px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                            disabled={actionLoading[clerk.id]}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleStatusToggle(clerk.id, clerk.status)}
                            className="button-action px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                            disabled={actionLoading[clerk.id]}
                          >
                            {actionLoading[clerk.id]
                              ? 'Processing...'
                              : clerk.status === 'ACTIVE'
                              ? 'Deactivate'
                              : 'Activate'}
                          </button>
                          <button
                            onClick={() => handleDelete(clerk.id)}
                            className="button-action px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700"
                            disabled={actionLoading[clerk.id]}
                          >
                            {actionLoading[clerk.id] ? 'Processing...' : 'Delete'}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="text-center text-gray-500 p-3">
                    No clerks found
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="flex justify-between items-center mt-4">
            <button
              className="pagination-button px-3 py-1 rounded-lg bg-gray-200 text-gray-700 disabled:opacity-50"
              onClick={() => paginate(currentPage - 1)}
              disabled={currentPage === 1}
            >
              Previous
            </button>
            <div className="flex gap-2">
              {Array.from({ length: totalPages }, (_, i) => (
                <button
                  key={i + 1}
                  className={`pagination-button px-3 py-1 rounded-lg ${
                    currentPage === i + 1
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-200 text-gray-700'
                  }`}
                  onClick={() => paginate(i + 1)}
                >
                  {i + 1}
                </button>
              ))}
            </div>
            <button
              className="pagination-button px-3 py-1 rounded-lg bg-gray-200 text-gray-700 disabled:opacity-50"
              onClick={() => paginate(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(ClerkManagement);