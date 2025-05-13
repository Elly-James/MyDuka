import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { logout } from '../store/slices/authSlice';
import { FaBars, FaUserFriends, FaBox, FaMoneyBillWave, FaChartLine, FaClipboardList, FaSignOutAlt } from 'react-icons/fa';
import './admin.css';

const SideBar = () => {
  const dispatch = useDispatch();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (path) => (location.pathname === path ? 'active' : '');

  const handleLogout = () => {
    dispatch(logout());
  };

  return (
    <aside className={`admin-sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header flex items-center justify-between p-4">
        {!collapsed && <h3 className="sidebar-title">Admin Dashboard</h3>}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-white hover:text-purple-400 focus:outline-none"
        >
          <FaBars size={20} />
        </button>
      </div>
      <nav className="sidebar-nav">
        <Link
          to="/admin/clerk-management"
          className={`sidebar-link ${isActive('/admin/clerk-management')}`}
        >
          <FaUserFriends className="sidebar-icon" />
          {!collapsed && 'Clerk Management'}
        </Link>
        <Link
          to="/admin/inventory"
          className={`sidebar-link ${isActive('/admin/inventory')}`}
        >
          <FaBox className="sidebar-icon" />
          {!collapsed && 'Inventory'}
        </Link>
        <Link
          to="/admin/payments"
          className={`sidebar-link ${isActive('/admin/payments')}`}
        >
          <FaMoneyBillWave className="sidebar-icon" />
          {!collapsed && 'Payments'}
        </Link>
        <Link
          to="/admin/reports"
          className={`sidebar-link ${isActive('/admin/reports')}`}
        >
          <FaChartLine className="sidebar-icon" />
          {!collapsed && 'Reports'}
        </Link>
        <Link
          to="/admin/supply-requests"
          className={`sidebar-link ${isActive('/admin/supply-requests')}`}
        >
          <FaClipboardList className="sidebar-icon" />
          {!collapsed && 'Supply Requests'}
        </Link>
        <button onClick={handleLogout} className="sidebar-logout">
          <FaSignOutAlt className="sidebar-icon" />
          {!collapsed && 'Logout'}
        </button>
      </nav>
    </aside>
  );
};

export default SideBar;