import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';

const SideBar = () => {
  const { setUser } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    navigate('/login');
  };

  return (
    <div className="w-64 bg-blue-900 text-white h-screen p-4">
      <h1 className="text-2xl font-bold mb-8">MyDuka</h1>
      <nav className="space-y-4">
        <button onClick={() => navigate('/merchant-dashboard')} className="w-full text-left p-2 rounded bg-blue-700 hover:bg-blue-600">
          Dashboard
        </button>
        <button onClick={() => navigate('/merchant/admin-management')} className="w-full text-left p-2 rounded hover:bg-blue-700">
          Admin Management
        </button>
        <button onClick={() => navigate('/merchant/store-reports')} className="w-full text-left p-2 rounded hover:bg-blue-700">
          Store Reports
        </button>
        <button onClick={() => navigate('/merchant/payment-tracking')} className="w-full text-left p-2 rounded hover:bg-blue-700">
          Payment Tracking
        </button>
        <button onClick={handleLogout} className="w-full text-left p-2 rounded hover:bg-red-700">
          Logout
        </button>
      </nav>
    </div>
  );
};

export default SideBar;