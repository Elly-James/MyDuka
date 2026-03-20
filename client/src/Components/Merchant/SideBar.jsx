import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/slices/authSlice';
import './merchant.css';
import { FaChevronLeft, FaChevronRight } from 'react-icons/fa';

const SideBar = () => {
  const dispatch = useDispatch();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (path) => (location.pathname === path ? 'active' : '');

  const handleLogout = () => {
    dispatch(logout());
  };

  const toggleSidebar = () => {
    setCollapsed(!collapsed);
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <button className="sidebar-toggle" onClick={toggleSidebar}>
        {collapsed ? <FaChevronRight /> : <FaChevronLeft />}
      </button>

      <nav className="sidebar-nav">
        <Link to="/merchant/dashboard" className={`sidebar-link ${isActive('/merchant/dashboard')}`}>
          <span className="sidebar-icon">📊</span>
          {!collapsed && <span>Dashboard</span>}
        </Link>
        <Link to="/merchant/admin-management" className={`sidebar-link ${isActive('/merchant/admin-management')}`}>
          <span className="sidebar-icon">👥</span>
          {!collapsed && <span>Admin Management</span>}
        </Link>
        <Link to="/merchant/store-reports" className={`sidebar-link ${isActive('/merchant/store-reports')}`}>
          <span className="sidebar-icon">📋</span>
          {!collapsed && <span>Store Reports</span>}
        </Link>
        <Link to="/merchant/payment-tracking" className={`sidebar-link ${isActive('/merchant/payment-tracking')}`}>
          <span className="sidebar-icon">💰</span>
          {!collapsed && <span>Payment Tracking</span>}
        </Link>
      </nav>

      {/* Logout section (matches your CSS) */}
      <div className="sidebar-footer">
        <button onClick={handleLogout} className="sidebar-logout">
          <span className="sidebar-icon">🚪</span>
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
};

export default SideBar;