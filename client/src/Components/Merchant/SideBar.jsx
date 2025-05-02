import React, { useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import './merchant.css';

const SideBar = () => {
  const navigate = useNavigate();
  const { logout } = useContext(AuthContext);
  const location = useLocation();

  const isActive = (path) => location.pathname === path ? 'active' : '';

  return (
    <aside className="sidebar">
      <h3 className="sidebar-title">MyDuka</h3>
      <nav className="sidebar-nav">
        <button onClick={() => navigate('/merchant/dashboard')} className={`sidebar-link ${isActive('/merchant/dashboard')}`}>
          Dashboard
        </button>
        <button onClick={() => navigate('/merchant/admin-management')} className={`sidebar-link ${isActive('/merchant/admin-management')}`}>
          Admin Management
        </button>
        <button onClick={() => navigate('/merchant/store-reports')} className={`sidebar-link ${isActive('/merchant/store-reports')}`}>
          Store Reports
        </button>
        <button onClick={() => navigate('/merchant/payment-tracking')} className={`sidebar-link ${isActive('/merchant/payment-tracking')}`}>
          Payment Tracking
        </button>
        <button onClick={logout} className="sidebar-logout">Logout</button>
      </nav>
    </aside>
  );
};

export default SideBar;