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
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      { label: 'Sales', data: [20000, 40000, 30000, 60000, 70000, 50000, 80000], borderColor: '#2E3A8C', tension: 0.4, fill: false },
    ],
  };

  return (
    <div className="merchant-container">
      <SideBar />
      <div className="main-content">
        {error && <p className="text-red-500 mb-4">{error}</p>}

        <div className="card">
          <h2 className="card-title">Reports</h2>
          <div className="flex justify-between mb-4">
            <div className="flex gap-4">
              <button className="button button-primary active">Weekly</button>
              <button className="button button-primary">Monthly</button>
              <button className="button button-primary">Annual</button>
            </div>
            <button className="button button-primary">EXPORT PDF</button>
          </div>
          <div className="mb-6">
            <Bar data={chartData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }} />
          </div>
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">Top Selling Products</h3>
            <table className="table w-full">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Units Sold</th>
                  <th>Revenue (KSh)</th>
                  <th>Growth</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Rice (5kg)</td>
                  <td>215</td>
                  <td>107,500</td>
                  <td className="text-green-600">+15%</td>
                </tr>
                <tr>
                  <td>Milk (500ml)</td>
                  <td>189</td>
                  <td>11,340</td>
                  <td className="text-green-600">+8%</td>
                </tr>
                <tr>
                  <td>Sugar (1kg)</td>
                  <td>146</td>
                  <td>17,520</td>
                  <td className="text-red-600">-3%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;