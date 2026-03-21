// src/NavBar/NavBar.jsx
// Fix: watches the sidebar DOM for the 'collapsed' class via MutationObserver
// and applies .sidebar-collapsed to the navbar so left: var(--sidebar-w-sm)
// kicks in — eliminating the white gap on the right side.

import React, { useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import './navbar.css';

const NavBar = () => {
  const { user, logout, loading } = useContext(AuthContext);
  const navigate = useNavigate();

  // Track whether the sidebar is collapsed so we can shift the navbar left
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;

    // Set initial state (e.g. if page refreshes while collapsed)
    setSidebarCollapsed(sidebar.classList.contains('collapsed'));

    // Watch for class changes on the sidebar element
    const observer = new MutationObserver(() => {
      setSidebarCollapsed(sidebar.classList.contains('collapsed'));
    });

    observer.observe(sidebar, {
      attributes: true,
      attributeFilter: ['class'],
    });

    return () => observer.disconnect();
  }, []);

  if (loading) return null;
  if (!user)   return null;

  const getDashboardRoute = () => {
    if (user.role === 'MERCHANT') return '/merchant/dashboard';
    if (user.role === 'ADMIN')    return '/admin/dashboard';
    return '/clerk/stock-entry';
  };

  const getInitials = (name) => {
    if (!name) return 'U';
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <nav className={`navbar${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      <div className="navbar-container">

        {/* ── Logo ── */}
        <div className="navbar-left">
          <div
            className="navbar-logo"
            onClick={() => navigate(getDashboardRoute())}
          >
            {/* span instead of h1 — avoids browser default margins */}
            <span className="logo-text">MyDuka</span>
          </div>
        </div>

        {/* ── User Info + Logout ── */}
        <div className="navbar-right">
          <div className="navbar-user">
            <div className="user-info">
              <div className="user-avatar">
                {getInitials(user?.name)}
              </div>
              <div className="user-details">
                <span className="user-name">{user?.name || 'User'}</span>
                <span className="user-role">{user?.role || ''}</span>
              </div>
            </div>
          </div>

          <button onClick={logout} className="logout-button">
            Logout
          </button>
        </div>

      </div>
    </nav>
  );
};

export default NavBar;