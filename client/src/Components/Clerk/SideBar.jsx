// src/Components/Clerk/SideBar.jsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/slices/authSlice';
import './clerk.css';

const SideBar = () => {
  const dispatch = useDispatch();
  const location = useLocation();

  const isActive = (path) => (location.pathname === path ? 'active' : '');

  const handleLogout = () => {
    dispatch(logout());
  };

  return (
    <aside className="clerk-sidebar">
      <h3 className="sidebar-title">MyDuka</h3>
      <nav className="sidebar-nav">
        <Link
          to="/clerk/stock-entry"
          className={`sidebar-link ${isActive('/clerk/stock-entry')}`}
        >
          <span className="sidebar-icon">📦</span> Stock Entry
        </Link>
        <Link
          to="/clerk/stock-alerts"
          className={`sidebar-link ${isActive('/clerk/stock-alerts')}`}
        >
          <span className="sidebar-icon">⚠️</span> Stock Alerts
        </Link>
        <Link
          to="/clerk/activity-log"
          className={`sidebar-link ${isActive('/clerk/activity-log')}`}
        >
          <span className="sidebar-icon">📝</span> Activity Log
        </Link>
        <button onClick={handleLogout} className="sidebar-logout">
          <span className="sidebar-icon">🚪</span> Logout
        </button>
      </nav>
    </aside>
  );
};

export default SideBar;