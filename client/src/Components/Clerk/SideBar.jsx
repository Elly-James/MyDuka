// src/Components/Clerk/SideBar.jsx
import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const SideBar = () => {
  const navigate = useNavigate();
  const { logout } = useContext(AuthContext);

  return (
    <div className="sidebar w-64 bg-gray-800 text-white h-full">
      <h3 className="text-xl font-bold p-4">Clerk Dashboard</h3>
      <nav className="space-y-2">
        <a
          onClick={() => navigate('/clerk/activity-log')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Activity Log
        </a>
        <a
          onClick={() => navigate('/clerk/stock-alerts')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Stock Alerts
        </a>
        <a
          onClick={() => navigate('/clerk/stock-entry')}
          className="block p-4 hover:bg-gray-700 cursor-pointer"
        >
          Stock Entry
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