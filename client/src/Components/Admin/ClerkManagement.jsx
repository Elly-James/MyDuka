
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const ClerkManagement = () => {
  const [clerks, setClerks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    store: 'Nairobi Central',
    accessLevel: 'standard'
  });
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Sample chart data - Replace with actual API data later
  const chartData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Jane Smith',
        data: [65, 59, 80, 81, 56, 55],
        fill: false,
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1
      },
      {
        label: 'John Doe',
        data: [28, 48, 40, 19, 86, 27],
        fill: false,
        borderColor: 'rgb(255, 99, 132)',
        tension: 0.1
      },
      {
        label: 'Sarah Johnson',
        data: [33, 25, 35, 51, 54, 76],
        fill: false,
        borderColor: 'rgb(53, 162, 235)',
        tension: 0.1
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Clerk Performance'
      }
    }
  };

  useEffect(() => {
    // Fetch clerks from API
    const fetchClerks = async () => {
      try {
        setLoading(true);
        // Replace with actual API endpoint
        const response = await axios.get('http://localhost:5000/api/users?role=CLERK', {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        });
        setClerks(response.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch clerks. Please try again later.');
        setLoading(false);
        console.error('Error fetching clerks:', err);
      }
    };

    fetchClerks();
  }, []);

  // For demo purposes, using sample data if API fails
  useEffect(() => {
    if (error) {
      // Sample clerk data
      setClerks([
        { id: 1, name: 'Jane Smith', email: 'jane@myduka.com', lastActive: '2025-04-29', status: 'Active' },
        { id: 2, name: 'John Doe', email: 'john@myduka.com', lastActive: '2025-04-28', status: 'Active' },
        { id: 3, name: 'Sarah Johnson', email: 'sarah@myduka.com', lastActive: '2025-04-25', status: 'Inactive' },
        { id: 4, name: 'David Lee', email: 'david@myduka.com', lastActive: '2025-04-27', status: 'Active' },
        { id: 5, name: 'Maria Garcia', email: 'maria@myduka.com', lastActive: '2025-04-26', status: 'Active' },
        { id: 6, name: 'Robert Chen', email: 'robert@myduka.com', lastActive: '2025-04-24', status: 'Inactive' },
      ]);
    }
  }, [error]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      // Replace with actual API endpoint
      await axios.post('http://localhost:5000/api/users/invite', 
        {
          name: formData.fullName,
          email: formData.email,
          store: formData.store,
          role: 'CLERK',
          accessLevel: formData.accessLevel
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      
      // Success! Close modal and refresh list
      setShowInviteModal(false);
      // Refresh clerk list
      const response = await axios.get('http://localhost:5000/api/users?role=CLERK', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`
        }
      });
      setClerks(response.data);
      
      // Reset form
      setFormData({
        fullName: '',
        email: '',
        store: 'Nairobi Central',
        accessLevel: 'standard'
      });
      
    } catch (err) {
      console.error('Error inviting clerk:', err);
      alert('Failed to send invitation. Please try again.');
    }
  };

  const handleStatusChange = async (clerkId, currentStatus) => {
    try {
      const newStatus = currentStatus === 'Active' ? 'Inactive' : 'Active';
      
      // Replace with actual API endpoint
      await axios.put(`http://localhost:5000/api/users/${clerkId}/status`, 
        { status: newStatus.toLowerCase() },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      
      // Update local state
      setClerks(clerks.map(clerk => 
        clerk.id === clerkId 
          ? { ...clerk, status: newStatus } 
          : clerk
      ));
      
    } catch (err) {
      console.error('Error updating clerk status:', err);
      alert('Failed to update status. Please try again.');
    }
  };

  const handleDelete = async (clerkId) => {
    if (!window.confirm('Are you sure you want to delete this clerk?')) {
      return;
    }
    
    try {
      // Replace with actual API endpoint
      await axios.delete(`http://localhost:5000/api/users/${clerkId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      // Remove from local state
      setClerks(clerks.filter(clerk => clerk.id !== clerkId));
      
    } catch (err) {
      console.error('Error deleting clerk:', err);
      alert('Failed to delete clerk. Please try again.');
    }
  };

  // Pagination logic
  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentClerks = clerks.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(clerks.length / itemsPerPage);

  return (
    <div className="p-6 w-full">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Clerk Management</h1>
        <button 
          onClick={() => setShowInviteModal(true)}
          className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded"
        >
          + Add Clerk
        </button>
      </div>

      {/* Clerks Table */}
      <div className="bg-white rounded-lg shadow mb-8">
        <div className="overflow-x-auto">
          <table className="w-full table-auto">
            <thead>
              <tr className="bg-gray-50 text-left">
                <th className="px-6 py-3 text-gray-600 font-semibold">Name</th>
                <th className="px-6 py-3 text-gray-600 font-semibold">Email</th>
                <th className="px-6 py-3 text-gray-600 font-semibold">Last Active</th>
                <th className="px-6 py-3 text-gray-600 font-semibold">Status</th>
                <th className="px-6 py-3 text-gray-600 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" className="text-center py-4">Loading...</td>
                </tr>
              ) : currentClerks.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-4">No clerks found</td>
                </tr>
              ) : (
                currentClerks.map((clerk) => (
                  <tr key={clerk.id} className="border-t border-gray-100">
                    <td className="px-6 py-4">{clerk.name}</td>
                    <td className="px-6 py-4">{clerk.email}</td>
                    <td className="px-6 py-4">{clerk.lastActive}</td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-sm ${
                        clerk.status === 'Active' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {clerk.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex space-x-2">
                        <button 
                          onClick={() => handleStatusChange(clerk.id, clerk.status)}
                          className="text-gray-500 hover:text-gray-700"
                          title={clerk.status === 'Active' ? 'Deactivate' : 'Activate'}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                          </svg>
                        </button>
                        <button 
                          onClick={() => handleDelete(clerk.id)}
                          className="text-red-500 hover:text-red-700"
                          title="Delete"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        {clerks.length > itemsPerPage && (
          <div className="flex justify-center space-x-1 p-4">
            <button 
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className={`px-3 py-1 rounded ${
                currentPage === 1 
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              &lt;
            </button>
            
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`px-3 py-1 rounded ${
                  currentPage === page
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {page}
              </button>
            ))}
            
            <button 
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
              className={`px-3 py-1 rounded ${
                currentPage === totalPages 
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              &gt;
            </button>
          </div>
        )}
      </div>

      {/* Performance Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Clerk Performance</h2>
        <div className="h-64">
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>

      {/* Invite Clerk Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Invite Clerk</h2>
              <button 
                onClick={() => setShowInviteModal(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <h3 className="text-lg font-medium mb-2">Clerk Details</h3>
                
                <div className="mb-4">
                  <label className="block text-gray-700 mb-2">Full Name</label>
                  <input
                    type="text"
                    name="fullName"
                    value={formData.fullName}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>
                
                <div className="mb-4">
                  <label className="block text-gray-700 mb-2">Email Address</label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>
                
                <div className="mb-4">
                  <label className="block text-gray-700 mb-2">Store</label>
                  <select
                    name="store"
                    value={formData.store}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="Nairobi Central">Nairobi Central</option>
                    <option value="Downtown Branch">Downtown Branch</option>
                    <option value="Mall Outlet">Mall Outlet</option>
                  </select>
                </div>
                
                <div className="mb-4">
                  <label className="block text-gray-700 mb-2">Access Level</label>
                  <div className="flex space-x-4">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="accessLevel"
                        value="standard"
                        checked={formData.accessLevel === 'standard'}
                        onChange={handleInputChange}
                        className="mr-2"
                      />
                      Standard Access
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        name="accessLevel"
                        value="limited"
                        checked={formData.accessLevel === 'limited'}
                        onChange={handleInputChange}
                        className="mr-2"
                      />
                      Limited Access
                    </label>
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
                >
                  Send Invitation
                </button>
              </div>
            </form>
            
            <div className="mt-4 p-3 bg-blue-50 text-blue-700 rounded-md flex items-start">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
              </svg>
              <span className="text-sm">
                An email with registration instructions will be sent to the clerk.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClerkManagement;
=======
// src/Components/Admin/Dashboard.jsx
import React from 'react';
import SideBar from './SideBar';

const Dashboard = () => (
  <div className="flex h-screen bg-gray-100">
    <SideBar />
    <div className="flex-1 p-6">
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard (Placeholder)</h1>
      <p>This feature will be implemented soon.</p>
    </div>
  </div>
);

export default Dashboard;

