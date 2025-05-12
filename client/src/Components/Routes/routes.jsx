import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { useContext } from 'react';

// Components
import LoginPage from '../LoginPage/LoginPage.jsx';
import ForgotPassword from '../LoginPage/ForgotPassword.jsx';
import ResetPassword from '../LoginPage/ResetPassword.jsx';

// Merchant Components
import MerchantDashboard from '../Merchant/Dashboard.jsx';
import AdminManagement from '../Merchant/AdminManagement.jsx';
import PaymentTracking from '../Merchant/PaymentTracking.jsx';
import StoreReports from '../Merchant/StoreReports.jsx';

// Admin Components

import ClerkManagement from '../Admin/ClerkManagement.jsx';
import InventoryOverview from '../Admin/InventoryOverview.jsx';
import AdminPayments from '../Admin/Payments.jsx';
import AdminReports from '../Admin/Reports.jsx';
import SupplyRequests from '../Admin/SupplyRequests.jsx';

// Clerk Components
import ActivityLog from '../Clerk/ActivityLog.jsx';
import StockAlerts from '../Clerk/StockAlerts.jsx';
import StockEntry from '../Clerk/StockEntry.jsx';

// Error Boundary Component
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6">
          <h2 className="text-2xl font-bold text-red-600">Something went wrong.</h2>
          <p>{this.state.error?.message || 'An unexpected error occurred.'}</p>
          <button
            className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg"
            onClick={() => window.location.reload()}
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useContext(AuthContext);
  const location = useLocation();

  if (loading) {
    return <div>Loading...</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (!allowedRoles.includes(user.role)) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return children;
};

const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/" element={<LoginPage />} />

      {/* Merchant Routes */}
      <Route
        path="/merchant/dashboard"
        element={
          <ProtectedRoute allowedRoles={['MERCHANT']}>
            <ErrorBoundary>
              <MerchantDashboard />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/merchant/admin-management"
        element={
          <ProtectedRoute allowedRoles={['MERCHANT']}>
            <ErrorBoundary>
              <AdminManagement />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/merchant/payment-tracking"
        element={
          <ProtectedRoute allowedRoles={['MERCHANT']}>
            <ErrorBoundary>
              <PaymentTracking />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/merchant/store-reports"
        element={
          <ProtectedRoute allowedRoles={['MERCHANT']}>
            <ErrorBoundary>
              <StoreReports />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />

      {/* Admin Routes */}
      <Route
        path="/admin/dashboard"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <ErrorBoundary>
           
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/clerk-management"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <ErrorBoundary>
              <ClerkManagement />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/inventory"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <ErrorBoundary>
              <InventoryOverview />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/payments"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <ErrorBoundary>
              <AdminPayments />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <ErrorBoundary>
              <AdminReports />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/supply-requests"
        element={
          <ProtectedRoute allowedRoles={['ADMIN']}>
            <ErrorBoundary>
              <SupplyRequests />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />

      {/* Clerk Routes */}
      <Route
        path="/clerk/activity-log"
        element={
          <ProtectedRoute allowedRoles={['CLERK']}>
            <ErrorBoundary>
              <ActivityLog />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/clerk/stock-alerts"
        element={
          <ProtectedRoute allowedRoles={['CLERK']}>
            <ErrorBoundary>
              <StockAlerts />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
      <Route
        path="/clerk/stock-entry"
        element={
          <ProtectedRoute allowedRoles={['CLERK']}>
            <ErrorBoundary>
              <StockEntry />
            </ErrorBoundary>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

export default AppRoutes;