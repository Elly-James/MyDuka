import React, { useContext } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

// Components
// import LoginPage from '../Components/LoginPage/LoginPage';
// import RegisterPage from '../Components/LoginPage/RegisterPage';
// import ForgotPassword from '../Components/LoginPage/ForgotPassword';
// import ResetPassword from '../Components/LoginPage/ResetPassword';


import LoginPage from '../LoginPage/LoginPage';
import RegisterPage from '../LoginPage/RegisterPage';
import ForgotPassword from '../LoginPage/ForgotPassword';
import ResetPassword from '../LoginPage/ResetPassword';


// Merchant Components
// import MerchantDashboard from '../Components/Merchant/Dashboard';
// import AdminManage from '../Components/Merchant/AdminManage';
// import PaymentTracking from '../Components/Merchant/PaymentTracking';
// import StoreReports from '../Components/Merchant/StoreReports';


import MerchantDashboard from '../Merchant/Dashboard';
import AdminManage from '../Merchant/AdminManagement';
import PaymentTracking from '../Merchant/PaymentTracking';
import StoreReports from '../Merchant/StoreReports';

// Admin Components (placeholders, implement similarly to Merchant)
// import AdminDashboard from '../Components/Admin/Dashboard';
// import ClerkManagement from '../Components/Admin/ClerkManagement';
// import InventoryOverview from '../Components/Admin/InventoryOverview';
// import AdminPayments from '../Components/Admin/Payments';
// import AdminReports from '../Components/Admin/Reports';
// import SupplyRequests from '../Components/Admin/SupplyRequests';


import AdminDashboard from '../Admin/Dashboard';
import ClerkManagement from '../Admin/ClerkManagement';
import InventoryOverview from '../Admin/InventoryOverview';
import AdminPayments from '../Admin/Payments';
import AdminReports from '../Admin/Reports';
import SupplyRequests from '../Admin/SupplyRequests';

// Clerk Components (placeholders, implement similarly to Merchant)
// import ActivityLog from '../Components/Clerk/ActivityLog';
// import StockAlerts from '../Components/Clerk/StockAlerts';
// import StockEntry from '../Components/Clerk/StockEntry';


import ActivityLog from '../Clerk/ActivityLog';
import StockAlerts from '../Clerk/StockAlerts';
import StockEntry from '../Clerk/StockEntry';
// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user } = useContext(AuthContext);
  if (!user) {
    return <Navigate to="/login" />;
  }
  if (!allowedRoles.includes(user.role)) {
    return <Navigate to="/login" />;
  }
  return children;
};

const AppRoutes = () => (
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

export default AppRoutes;