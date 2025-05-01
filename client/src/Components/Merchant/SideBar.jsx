import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import './merchant.css';

const SideBar = () => {
  const navigate = useNavigate();
  const { logout } = useContext(AuthContext);

  return (
    <aside className="sidebar">
      <h3 className="sidebar-title">Merchant Dashboard</h3>
      <nav className="sidebar-nav">
        <button onClick={() => navigate('/merchant/dashboard')} className="sidebar-link">Dashboard</button>
        <button onClick={() => navigate('/merchant/admin-management')} className="sidebar-link">Admin Management</button>
        <button onClick={() => navigate('/merchant/payment-tracking')} className="sidebar-link">Payment Tracking</button>
        <button onClick={() => navigate('/merchant/store-reports')} className="sidebar-link">Store Reports</button>
        <button onClick={logout} className="sidebar-logout">Logout</button>
      </nav>
    </aside>
  );
};

export default SideBar;