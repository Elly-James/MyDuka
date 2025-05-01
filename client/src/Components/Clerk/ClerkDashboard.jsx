// src/pages/ClerkDashboard.jsx (assuming this is a page component)
import React from 'react';
import SideBar from '../Components/Clerk/SideBar';
import AddStockEntry from '../Components/Clerk/AddStockEntry';
import StockAlerts from '../Components/Clerk/StockAlerts';
import ActivityLog from '../Components/Clerk/ActivityLog';

const ClerkDashboard = () => {
  return (
    <div className="bg-gray-100 h-screen flex">
      {/* Sidebar */}
      <SideBar />

      {/* Main Content */}
      <div className="flex-1 p-4">
        {/* Top Bar (MyDuka, Clerk Dashboard, SJ) */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-semibold text-gray-800">Clerk Dashboard</h1>
          <div className="text-gray-600">SJ</div> {/* Placeholder for user info */}
        </div>

        {/* Main Content Sections */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Add Stock Entry */}
          <div className="bg-white p-4 rounded shadow border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Add Stock Entry</h3>
            <AddStockEntry /> {/* We'll create this component next */}
          </div>

          {/* Stock Alerts */}
          <div className="bg-white p-4 rounded shadow border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Stock Alerts</h3>
            <StockAlerts /> {/* We'll create this component next */}
          </div>
        </div>

        {/* Activity Log */}
        <ActivityLog /> {/* Your existing ActivityLog component */}
      </div>
    </div>
  );
};

export default ClerkDashboard;