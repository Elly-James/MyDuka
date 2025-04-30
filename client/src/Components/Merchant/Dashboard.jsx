import React, { useState, useEffect, useContext } from 'react';
import { Bar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { AuthContext } from '../../context/AuthContext';
import axios from 'axios';
import SideBar from './SideBar';
import './merchant.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const Dashboard = () => {
  const { user } = useContext(AuthContext);
  const [salesData, setSalesData] = useState(null);
  const [admins, setAdmins] = useState([]);
  const [unpaidSuppliers, setUnpaidSuppliers] = useState(12); // Static for now
  const [lowStockAlerts, setLowStockAlerts] = useState(5); // Static for now

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem('token');
        const config = { headers: { Authorization: `Bearer ${token}` } };

        // Fetch sales data
        const salesResponse = await axios.get('http://localhost:5000/api/reports/sales', config);
        setSalesData(salesResponse.data.chart_data);

        // Fetch admins
        const adminsResponse = await axios.get('http://localhost:5000/api/users?role=ADMIN', config);
        setAdmins(adminsResponse.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchData();
  }, []);

  const handleAddAdmin = () => {
    // Navigate to admin invitation page or open a modal (to be implemented)
    console.log('Add Admin clicked');
  };

  const handleDeactivate = async (id) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`http://localhost:5000/api/users/${id}/status`, { status: 'inactive' }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAdmins(admins.map(admin => admin.id === id ? { ...admin, status: 'inactive' } : admin));
    } catch (err) {
      console.error(err);
    }
  };

  const handleActivate = async (id) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`http://localhost:5000/api/users/${id}/status`, { status: 'active' }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAdmins(admins.map(admin => admin.id === id ? { ...admin, status: 'active' } : admin));
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`http://localhost:5000/api/users/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAdmins(admins.filter(admin => admin.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  const chartData = salesData ? {
    labels: salesData.labels,
    datasets: salesData.datasets,
  } : {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
    datasets: [
      { label: 'Sales', data: [65, 59, 80, 81, 56], backgroundColor: '#2E3A8C' },
      { label: 'Spoilage', data: [28, 48, 40, 19, 86], backgroundColor: '#FF6B6B' },
    ],
  };

  return (
    <div className="flex h-screen bg-gray-100">
      <SideBar />
      <div className="flex-1 p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Merchant Dashboard</h1>
          <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center">
            {user?.name?.charAt(0) || 'M'}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 mb-6">
          <div className="col-span-2 bg-white p-4 rounded shadow">
            <h2 className="text-lg font-semibold mb-4">Monthly Sales vs. Spoilage</h2>
            <Bar data={chartData} options={{ responsive: true }} />
          </div>
          <div className="space-y-4">
            <div className="bg-white p-4 rounded shadow">
              <h2 className="text-lg font-semibold">Unpaid Suppliers</h2>
              <p className="text-2xl font-bold">{unpaidSuppliers}</p>
            </div>
            <div className="bg-white p-4 rounded shadow">
              <h2 className="text-lg font-semibold">Low Stock Alerts</h2>
              <p className="text-2xl font-bold">{lowStockAlerts}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Admin Management</h2>
            <button onClick={handleAddAdmin} className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
              + Add Admin
            </button>
          </div>
          <table className="w-full">
            <thead>
              <tr className="text-left">
                <th className="p-2">Name</th>
                <th className="p-2">Email</th>
                <th className="p-2">Status</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {admins.map(admin => (
                <tr key={admin.id} className="border-t">
                  <td className="p-2">{admin.name}</td>
                  <td className="p-2">{admin.email}</td>
                  <td className="p-2">
                    <span className={`px-2 py-1 rounded ${admin.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {admin.status}
                    </span>
                  </td>
                  <td className="p-2 space-x-2">
                    {admin.status === 'active' ? (
                      <button onClick={() => handleDeactivate(admin.id)} className="text-blue-600 hover:underline">Deactivate</button>
                    ) : (
                      <button onClick={() => handleActivate(admin.id)} className="text-blue-600 hover:underline">Activate</button>
                    )}
                    <button onClick={() => handleDelete(admin.id)} className="text-red-600 hover:underline">Delete</button>
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