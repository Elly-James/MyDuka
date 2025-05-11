// src/Components/Clerk/SideBar.jsx
import React, { useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const SideBar = () => {
  const navigate = useNavigate();
  const { logout } = useContext(AuthContext);
  const location = useLocation();

  return (
    <div className="sidebar w-64 bg-gray-800 text-white h-full">
      <h3 className="text-xl font-bold p-4">MyDuka</h3> {/* Updated title to "MyDuka" */}
      <nav className="space-y-2 mt-4"> {/* Added some top margin for spacing */}
        <a
          onClick={() => navigate('/clerk/stock-entry')}
          className={`block p-4 hover:bg-gray-700 cursor-pointer ${
            location.pathname === '/clerk/stock-entry' ? 'bg-gray-700' : ''
          }`}
        >
          Stock Entry
        </a>
        <a
          onClick={() => navigate('/clerk/stock-alerts')}
          className={`block p-4 hover:bg-gray-700 cursor-pointer ${
            location.pathname === '/clerk/stock-alerts' ? 'bg-gray-700' : ''
          }`}
        >
          Stock Alerts
        </a>
        <a
          onClick={() => navigate('/clerk/activity-log')}
          className={`block p-4 hover:bg-gray-700 cursor-pointer ${
            location.pathname === '/clerk/activity-log' ? 'bg-gray-700' : ''
          }`}
        >
          Activity Log
        </a>
        <a
          onClick={logout}
          className="block p-4 hover:bg-gray-700 cursor-pointer mt-8" // Added some top margin for separation
        >
          Logout
        </a>
      </nav>
    </div>
  );
};

export default SideBar;