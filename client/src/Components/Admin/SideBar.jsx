// src/Components/Admin/SideBar.jsx
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/slices/authSlice';
import './admin.css';

const SideBar = () => {
  const dispatch = useDispatch();
  const location = useLocation();

  const isActive = (path) => (location.pathname === path ? 'active' : '');

  const handleLogout = () => {
    dispatch(logout());
  };

  return (
    <aside className="admin-sidebar">
      <h3 className="sidebar-title">Admin Dashboard</h3>
      <nav className="sidebar-nav">
        <Link
          to="/admin/clerk-management"
          className={`sidebar-link ${isActive('/admin/clerk-management')}`}
        >
          <span className="sidebar-icon">👥</span> Clerk Management
        </Link>
        <Link
          to="/admin/inventory"
          className={`sidebar-link ${isActive('/admin/inventory')}`}
        >
          <span className="sidebar-icon">📦</span> Inventory
        </Link>
        <Link
          to="/admin/payments"
          className={`sidebar-link ${isActive('/admin/payments')}`}
        >
          <span className="sidebar-icon">💰</span> Payments
        </Link>
        <Link
          to="/admin/reports"
          className={`sidebar-link ${isActive('/admin/reports')}`}
        >
          <span className="sidebar-icon">📊</span> Reports
        </Link>
        <Link
          to="/admin/supply-requests"
          className={`sidebar-link ${isActive('/admin/supply-requests')}`}
        >
          <span className="sidebar-icon">📋</span> Supply Requests
        </Link>
        <button onClick={handleLogout} className="sidebar-logout">
          <span className="sidebar-icon">🚪</span> Logout
        </button>
      </nav>
    </aside>
  );
};

export default SideBar;