import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';
import '../merchant.css';

const SideBar = () => {
  const navigate = useNavigate();
  const { logout } = useContext(AuthContext);

  return (
    <div className="merchant-sidebar">
      <h3>Merchant Dashboard</h3>
      <a onClick={() => navigate('/merchant/dashboard')}>Dashboard</a>
      <a onClick={() => navigate('/merchant/admin-management')}>Admin Management</a>
      <a onClick={() => navigate('/merchant/payment-tracking')}>Payment Tracking</a>
      <a onClick={() => navigate('/merchant/store-reports')}>Store Reports</a>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

export default SideBar;