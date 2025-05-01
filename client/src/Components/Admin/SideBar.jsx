// src/Components/Admin/SideBar.jsx
import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const SideBar = () => {
  const navigate = useNavigate();
  const { logout } = useContext(AuthContext);

  return (
    <div className="sidebar w-64 bg-gray-800 text-white h-full">
      <h3 className="text-xl font-bold p-4">Admin Dashboard</h3>
      <nav className="space-y-2">
        <a
          onClick={() => navigate('/admin/dashboard')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Dashboard
        </a>
        <a
          onClick={() => navigate('/admin/clerk-management')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Clerk Management
        </a>
        <a
          onClick={() => navigate('/admin/inventory')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Inventory
        </a>
        <a
          onClick={() => navigate('/admin/payments')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Payments
        </a>
        <a
          onClick={() => navigate('/admin/reports')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Reports
        </a>
        <a
          onClick={() => navigate('/admin/supply-requests')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Supply Requests
        </a>
        <a
          onClick={logout}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Logout
        </a>
      </nav>
    </div>
  );
};

export default SideBar;