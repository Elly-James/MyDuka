// src/Components/Admin/Dashboard.jsx
import React from 'react';
import SideBar from './SideBar';

const Dashboard = () => (
  <div className="flex h-screen bg-gray-100">
    <SideBar />
    <div className="flex-1 p-6">
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard (Placeholder)</h1>
      <p>This feature will be implemented soon.</p>
    </div>
  </div>
);

export default Dashboard;