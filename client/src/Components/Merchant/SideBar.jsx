import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/slices/authSlice';
import './merchant.css';

const SideBar = () => {
  const dispatch = useDispatch();
  const location = useLocation();

  const isActive = (path) => (location.pathname === path ? 'active' : '');

  const handleLogout = () => {
    dispatch(logout());
  };

  return (
    <aside className="sidebar">
      <h3 className="sidebar-title">MyDuka</h3>
      <nav className="sidebar-nav">
        <Link
          to="/merchant/dashboard"
          className={`sidebar-link ${isActive('/merchant/dashboard')}`}
        >
          <span className="sidebar-icon">📊</span> Dashboard
        </Link>
        <Link
          to="/merchant/admin-management"
          className={`sidebar-link ${isActive('/merchant/admin-management')}`}
        >
          <span className="sidebar-icon">👥</span> Admin Management
        </Link>
        <Link
          to="/merchant/store-reports"
          className={`sidebar-link ${isActive('/merchant/store-reports')}`}
        >
          <span className="sidebar-icon">📋</span> Store Reports
        </Link>
        <Link
          to="/merchant/payment-tracking"
          className={`sidebar-link ${isActive('/merchant/payment-tracking')}`}
        >
          <span className="sidebar-icon">💰</span> Payment Tracking
        </Link>
        <button onClick={handleLogout} className="sidebar-logout">
          <span className="sidebar-icon">🚪</span> Logout
        </button>
      </nav>
    </aside>
  );
};

export default SideBar;