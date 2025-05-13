import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import './navbar.css';

const NavBar = () => {
  const { user, logout, loading } = useContext(AuthContext);
  const navigate = useNavigate();

  if (loading) return null; // Wait until loading is complete
  if (!user) return null; // Don't show NavBar on public pages (e.g., login)

  return (
    <nav className="navbar">
      <div className="navbar-container">
        {/* Logo */}
        <div className="navbar-logo" onClick={() => navigate(user.role === 'MERCHANT' ? '/merchant/dashboard' : user.role === 'ADMIN' ? '/admin/dashboard' : '/clerk/stock-entry')}>
          <h1 className="logo-text">MyDuka</h1>
        </div>

        {/* User Info and Actions */}
        <div className="navbar-user">
          <div className="user-info">
            <div className="user-avatar">
              {user?.name?.charAt(0) || 'U'}
            </div>
            <span className="user-name">{user?.name || 'User'}</span>
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