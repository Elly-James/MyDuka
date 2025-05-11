
import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const SideBar = () => {
  const location = useLocation();
  const { logout } = useAuth();
  const [activeLink, setActiveLink] = useState('');

  useEffect(() => {
    // Extract the current page from URL path
    const path = location.pathname.split('/')[2] || 'dashboard';
    setActiveLink(path);
  }, [location]);

  const navLinks = [
    { name: 'Dashboard', path: '/admin-dashboard', icon: '📊' },
    { name: 'Clerk Management', path: '/admin-dashboard/clerk-management', icon: '👥' },
    { name: 'Inventory', path: '/admin-dashboard/inventory', icon: '📦' },
    { name: 'Supply Requests', path: '/admin-dashboard/supply-requests', icon: '📝' },
    { name: 'Reports', path: '/admin-dashboard/reports', icon: '📈' },
    { name: 'Payments', path: '/admin-dashboard/payments', icon: '💰' },
  ];

  const handleLogout = () => {
    logout();
    // Navigate is handled by AuthContext
  };

  return (
    <div className="h-full min-h-screen w-64 bg-indigo-800 text-white flex flex-col">
      <div className="p-6 border-b border-indigo-700">
        <Link to="/admin-dashboard" className="text-2xl font-bold">MyDuka</Link>
      </div>
      
      <nav className="flex-1">
        <ul className="mt-6">
          {navLinks.map((link) => (
            <li key={link.path} className="mb-1">
              <Link
                to={link.path}
                className={`flex items-center px-6 py-3 text-lg transition-colors duration-200 ${
                  activeLink === link.path.split('/')[2] || 
                  (activeLink === 'dashboard' && link.path === '/admin-dashboard')
                    ? 'bg-indigo-900 border-l-4 border-white'
                    : 'hover:bg-indigo-700'
                }`}
              >
                <span className="mr-3">{link.icon}</span>
                {link.name}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      
      <div className="p-6 border-t border-indigo-700">
        <button
          onClick={handleLogout}
          className="flex items-center text-lg hover:text-gray-300 transition-colors duration-200"
        >
          <span className="mr-3">🚪</span>
          Logout
        </button>
      </div>
=======
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