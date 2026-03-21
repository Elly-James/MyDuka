import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/slices/authSlice';
import { FaChevronLeft, FaChevronRight, FaUserFriends, FaBox, FaMoneyBillWave, FaChartLine, FaClipboardList } from 'react-icons/fa';
import './admin.css';

const SideBar = () => {
  const dispatch  = useDispatch();
  const location  = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (path) => location.pathname === path ? 'active' : '';
  const handleLogout = () => dispatch(logout());
  const toggleSidebar = () => setCollapsed((prev) => !prev);

  return (
    <aside className={`admin-sidebar ${collapsed ? 'collapsed' : ''}`}>

      {/* ── Brand / Logo ── */}
      <div className="sidebar-header">
        <span className="sidebar-title">MyDuka Admin</span>
        <button
          className="sidebar-toggle-btn"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
        >
          {collapsed ? <FaChevronRight size={14} /> : <FaChevronLeft size={14} />}
        </button>
      </div>

      {/* ── Nav Links ── */}
      <nav className="sidebar-nav">

        <Link
          to="/admin/clerk-management"
          className={`sidebar-link ${isActive('/admin/clerk-management')}`}
          data-label="Clerk Management"
        >
          <span className="sidebar-icon"><FaUserFriends /></span>
          <span>Clerk Management</span>
        </Link>

        <Link
          to="/admin/inventory"
          className={`sidebar-link ${isActive('/admin/inventory')}`}
          data-label="Inventory"
        >
          <span className="sidebar-icon"><FaBox /></span>
          <span>Inventory</span>
        </Link>

        <Link
          to="/admin/payments"
          className={`sidebar-link ${isActive('/admin/payments')}`}
          data-label="Payments"
        >
          <span className="sidebar-icon"><FaMoneyBillWave /></span>
          <span>Payments</span>
        </Link>

        <Link
          to="/admin/reports"
          className={`sidebar-link ${isActive('/admin/reports')}`}
          data-label="Reports"
        >
          <span className="sidebar-icon"><FaChartLine /></span>
          <span>Reports</span>
        </Link>

        <Link
          to="/admin/supply-requests"
          className={`sidebar-link ${isActive('/admin/supply-requests')}`}
          data-label="Supply Requests"
        >
          <span className="sidebar-icon"><FaClipboardList /></span>
          <span>Supply Requests</span>
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