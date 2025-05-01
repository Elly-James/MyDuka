import React, { useContext } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

// Components
import LoginPage from '../LoginPage/LoginPage.jsx';
import RegisterPage from '../LoginPage/RegisterPage.jsx';
import ForgotPassword from '../LoginPage/ForgotPassword.jsx';
import ResetPassword from '../LoginPage/ResetPassword.jsx';

// Merchant Components
import MerchantDashboard from '../Merchant/Dashboard.jsx';
import AdminManage from '../Merchant/AdminManagement.jsx';
import PaymentTracking from '../Merchant/PaymentTracking.jsx';
import StoreReports from '../Merchant/StoreReports.jsx';

// Admin Components
import AdminDashboard from '../Admin/Dashboard.jsx';
import ClerkManagement from '../Admin/ClerkManagement.jsx';
import InventoryOverview from '../Admin/InventoryOverview.jsx';
import AdminPayments from '../Admin/Payments.jsx';
import AdminReports from '../Admin/Reports.jsx';
import SupplyRequests from '../Admin/SupplyRequests.jsx';

// Clerk Components
import ActivityLog from '../Clerk/ActivityLog.jsx';
import StockAlerts from '../Clerk/StockAlerts.jsx';
import StockEntry from '../Clerk/StockEntry.jsx';

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useContext(AuthContext);
  console.log('ProtectedRoute - user:', user, 'loading:', loading);
  if (loading) {
    console.log('ProtectedRoute - Still loading, showing loading screen');
    return <div>Loading...</div>;
  }
  if (!user) {
    console.log('ProtectedRoute - No user, redirecting to /login');
    return <Navigate to="/login" replace />;
  }
  if (!allowedRoles.includes(user.role)) {
    console.log(`ProtectedRoute - Role ${user.role} not allowed for ${allowedRoles}, redirecting to /login`);
    return <Navigate to="/login" replace />;
  }
  console.log('ProtectedRoute - Access granted, rendering children');
  return children;
};

const AppRoutes = () => {
  const { loading } = useContext(AuthContext);
  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/" element={<LoginPage />} />

      {/* Merchant Routes */}
      <Route
        path="/merchant/dashboard"
        element={
          <ProtectedRoute allowedRoles={['MERCHANT']}>
            <MerchantDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/merchant/admin-management"
        element={
          <ProtectedRoute allowedRoles={['MERCHANT']}>
            <AdminManage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/merchant/payment-tracking"
        element={
          <ProtectedRoute allowedRoles={['MERCHANT']}>
            <PaymentTracking />
          </ProtectedRoute>
        }
      />
      <Route
        path="/merchant/store-reports"
        element={
          <ProtectedRoute allowedRoles={['MERCHANT']}>
            <StoreReports />
          </ProtectedRoute>
        }
      />

      {/* Admin Routes */}
      <Route
        path="/admin/dashboard"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/clerk-management"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <ClerkManagement />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/inventory"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <InventoryOverview />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/payments"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <AdminPayments />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <AdminReports />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/supply-requests"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <SupplyRequests />
          </ProtectedRoute>
        }
      />

      {/* Clerk Routes */}
      <Route
        path="/clerk/activity-log"
        element={
          <ProtectedRoute allowedRoles={['CLERK']}>
            <ActivityLog />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clerk/stock-alerts"
        element={
          <ProtectedRoute allowedRoles={['CLERK']}>
            <StockAlerts />
          </ProtectedRoute>
        }
      />
      <Route
        path="/clerk/stock-entry"
        element={
          <ProtectedRoute allowedRoles={['CLERK']}>
            <StockEntry />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

export default AppRoutes;