// src/Merchant/SideBar.jsx
// Fixed SideBar — syncs collapsed state so .main-content and .navbar
// both receive the correct margin/left offset automatically via CSS
// sibling selectors (.sidebar.collapsed ~ .main-content).

import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/slices/authSlice';
import './merchant.css';
import { FaChevronLeft, FaChevronRight } from 'react-icons/fa';

const SideBar = () => {
  const dispatch  = useDispatch();
  const location  = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (path) => (location.pathname === path ? 'active' : '');

  const handleLogout   = () => dispatch(logout());
  const toggleSidebar  = () => setCollapsed((prev) => !prev);

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>

      {/* ── Brand / Logo ── */}
      <div className="sidebar-brand">
        <span className="sidebar-title">MyDuka</span>
        <button
          className="sidebar-toggle"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
        >
          {collapsed ? <FaChevronRight /> : <FaChevronLeft />}
        </button>
      </div>

      {/* ── Nav Links ── */}
      <nav className="sidebar-nav">

        <Link
          to="/merchant/dashboard"
          className={`sidebar-link ${isActive('/merchant/dashboard')}`}
          data-label="Dashboard"
        >
          <span className="sidebar-icon">📊</span>
          <span className="sidebar-link-label">Dashboard</span>
        </Link>

        <Link
          to="/merchant/admin-management"
          className={`sidebar-link ${isActive('/merchant/admin-management')}`}
          data-label="Admin Management"
        >
          <span className="sidebar-icon">👥</span>
          <span className="sidebar-link-label">Admin Management</span>
        </Link>

        <Link
          to="/merchant/store-reports"
          className={`sidebar-link ${isActive('/merchant/store-reports')}`}
          data-label="Store Reports"
        >
          <span className="sidebar-icon">📋</span>
          <span className="sidebar-link-label">Store Reports</span>
        </Link>

        <Link
          to="/merchant/payment-tracking"
          className={`sidebar-link ${isActive('/merchant/payment-tracking')}`}
          data-label="Payment Tracking"
        >
          <span className="sidebar-icon">💰</span>
          <span className="sidebar-link-label">Payment Tracking</span>
        </Link>

      </nav>

      {/* ── Logout at bottom ── */}
      <div className="sidebar-footer">
        <button className="sidebar-logout" onClick={handleLogout}>
          <span className="sidebar-icon">🚪</span>
          <span>Logout</span>
        </button>
      </div>

    </aside>
  );
};

export default SideBar;