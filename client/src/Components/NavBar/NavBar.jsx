import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import './navbar.css';

const NavBar = () => {
  const { user, logout, loading } = useContext(AuthContext);
  const navigate = useNavigate();

  // Wait until loading is complete
  if (loading) return null;
  // Don't show NavBar on public pages (e.g., login)
  if (!user) return null;

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
    <nav className="navbar">
      <div className="navbar-container">

        {/* ── Logo ── */}
        <div className="navbar-left">
          <div
            className="navbar-logo"
            onClick={() => navigate(getDashboardRoute())}
          >
            <h1 className="logo-text">MyDuka</h1>
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