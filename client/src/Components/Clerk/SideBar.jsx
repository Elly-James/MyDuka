// src/Components/Clerk/SideBar.jsx
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/slices/authSlice';
import { FaChevronLeft, FaChevronRight } from 'react-icons/fa';
import './clerk.css';

const SideBar = () => {
  const dispatch  = useDispatch();
  const location  = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const isActive     = (path) => (location.pathname === path ? 'active' : '');
  const handleLogout  = () => dispatch(logout());
  const toggleSidebar = () => setCollapsed((prev) => !prev);

  return (
    <aside className={`clerk-sidebar ${collapsed ? 'collapsed' : ''}`}>

      {/* ── Brand / Logo ── */}
      <div className="sidebar-brand">
        <span className="sidebar-title">MyDuka</span>
        <button
          className="sidebar-toggle-btn"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
        >
          {collapsed ? <FaChevronRight size={13} /> : <FaChevronLeft size={13} />}
        </button>
      </div>

      {/* ── Nav Links ── */}
      <nav className="sidebar-nav">

        <Link
          to="/clerk/stock-entry"
          className={`sidebar-link ${isActive('/clerk/stock-entry')}`}
          data-label="Stock Entry"
        >
          <span className="sidebar-icon">📦</span>
          <span>Stock Entry</span>
        </Link>

        <Link
          to="/clerk/stock-alerts"
          className={`sidebar-link ${isActive('/clerk/stock-alerts')}`}
          data-label="Stock Alerts"
        >
          <span className="sidebar-icon">⚠️</span>
          <span>Stock Alerts</span>
        </Link>

        <Link
          to="/clerk/activity-log"
          className={`sidebar-link ${isActive('/clerk/activity-log')}`}
          data-label="Activity Log"
        >
          <span className="sidebar-icon">📝</span>
          <span>Activity Log</span>
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