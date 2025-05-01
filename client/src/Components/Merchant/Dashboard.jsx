import React, { useState, useEffect, useContext } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { AuthContext } from '../context/AuthContext';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import './merchant.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const Dashboard = () => {
  const { user } = useContext(AuthContext);
  const [salesData, setSalesData] = useState(null);
  const [admins, setAdmins] = useState([]);
  const [unpaidSuppliers, setUnpaidSuppliers] = useState(0);
  const [lowStockAlerts, setLowStockAlerts] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const salesResponse = await api.get('/api/reports/sales');
        setSalesData(salesResponse.data.chart_data);

        const adminsResponse = await api.get('/api/users?role=ADMIN');
        setAdmins(adminsResponse.data.users || []);

        const unpaidResponse = await api.get('/api/inventory/suppliers/unpaid');
        setUnpaidSuppliers(unpaidResponse.data.suppliers?.length || 0);

        const lowStockResponse = await api.get('/api/inventory/low-stock');
        setLowStockAlerts(lowStockResponse.data.items?.length || 0);

        setError('');
      } catch (err) {
        handleApiError(err, setError);
      }
    };
    fetchData();
  }, []);

  const handleAddAdmin = () => {
    window.location.href = '/merchant/admin-management';
  };

  const handleDeactivate = async (id) => {
    try {
      await api.put(`/api/users/${id}/status`, { status: 'inactive' });
      setAdmins(admins.map(admin => admin.id === id ? { ...admin, status: 'inactive' } : admin));
      setError('');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handleActivate = async (id) => {
    try {
      await api.put(`/api/users/${id}/status`, { status: 'active' });
      setAdmins(admins.map(admin => admin.id === id ? { ...admin, status: 'active' } : admin));
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
        setError('');
      } catch (err) {
        handleApiError(err, setError);
      }
    }
  };

  const chartData = salesData || {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
    datasets: [
      { label: 'Sales', data: [65, 59, 80, 81, 56], backgroundColor: '#2E3A8C' },
      { label: 'Spoilage', data: [28, 48, 40, 19, 86], backgroundColor: '#FF6B6B' },
    ],
  };

  return (
    <div className="merchant-container">
      <SideBar />
      <div className="main-content">
        {error && <p className="error">{error}</p>}

        <div className="dashboard-grid">
          <div className="card">
            <h2 className="card-title">Monthly Sales vs. Spoilage</h2>
            <Bar data={chartData} options={{ responsive: true }} />
          </div>
          <div className="stats-container">
            <div className="card stat-card">
              <h2 className="stat-title">Unpaid Suppliers</h2>
              <p className="stat-value">{unpaidSuppliers}</p>
            </div>
            <div className="card stat-card">
              <h2 className="stat-title">Low Stock Alerts</h2>
              <p className="stat-value">{lowStockAlerts}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="card-title">Admin Management</h2>
            <button onClick={handleAddAdmin} className="button button-primary">
              + Add Admin
            </button>
          </div>
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

export default Dashboard;