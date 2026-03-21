import React, { useState, useEffect } from 'react';
import { api, formatCurrency, formatDate, handleApiError } from '../utils/api';
import useSocket from '../hooks/useSocket';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import Footer from '../Footer/Footer';
import './admin.css';

const Payments = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('unpaid');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalUnpaid, setTotalUnpaid] = useState(0);
  const [totalPaid, setTotalPaid] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  const suppliersPerPage = 5;

  const { socket } = useSocket();

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError('');
      try {
        const storesResponse = await api.get('/api/stores');
        setStores(storesResponse.data.stores || []);

        const suppliersResponse = await api.get(
          `/api/inventory/suppliers/${filter}${selectedStore ? `?store_id=${selectedStore}` : ''}${
            searchTerm ? `${selectedStore ? '&' : '?'}search=${encodeURIComponent(searchTerm)}` : ''
          }`
        );
        setSuppliers(suppliersResponse.data.suppliers || []);

        const unpaidResponse = await api.get(
          `/api/inventory/suppliers/unpaid${selectedStore ? `?store_id=${selectedStore}` : ''}`
        );
        setTotalUnpaid(unpaidResponse.data.suppliers.reduce((sum, s) => sum + (s.amount_due || 0), 0));

        const paidResponse = await api.get(
          `/api/inventory/suppliers/paid${selectedStore ? `?store_id=${selectedStore}` : ''}`
        );
        setTotalPaid(paidResponse.data.suppliers.reduce((sum, s) => sum + (s.amount_due || 0), 0));

        setSuccess('Payment data loaded successfully');
        setTimeout(() => setSuccess(''), 3000);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    if (socket && typeof socket.on === 'function') {
      socket.on('payment_updated', () => { setSuccess('Payment status updated'); fetchData(); });
      socket.on('notification', (n) => { setSuccess(n.message); setTimeout(() => setSuccess(''), 4000); });
    }
    return () => {
      if (socket && typeof socket.off === 'function') {
        socket.off('payment_updated');
        socket.off('notification');
      }
    };
  }, [filter, searchTerm, selectedStore, socket]);

  const handlePay = async (entryId) => {
    try {
      await api.put(`/api/inventory/update-payment/${entryId}`);
      setSuppliers((prev) => prev.map((s) => s.id === entryId ? { ...s, payment_status: 'PAID' } : s));
      setSuccess('Payment marked as paid');
      setTimeout(() => setSuccess(''), 3000);
      const [unpaidRes, paidRes] = await Promise.all([
        api.get(`/api/inventory/suppliers/unpaid${selectedStore ? `?store_id=${selectedStore}` : ''}`),
        api.get(`/api/inventory/suppliers/paid${selectedStore ? `?store_id=${selectedStore}` : ''}`),
      ]);
      setTotalUnpaid(unpaidRes.data.suppliers.reduce((sum, s) => sum + (s.amount_due || 0), 0));
      setTotalPaid(paidRes.data.suppliers.reduce((sum, s) => sum + (s.amount_due || 0), 0));
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handleMarkAllPaid = async () => {
    try {
      const unpaidIds = suppliers.filter((s) => s.payment_status === 'UNPAID').map((s) => s.id);
      await Promise.all(unpaidIds.map((id) => api.put(`/api/inventory/update-payment/${id}`)));
      setSuppliers((prev) => prev.map((s) => unpaidIds.includes(s.id) ? { ...s, payment_status: 'PAID' } : s));
      setTotalUnpaid(0);
      const paidRes = await api.get(
        `/api/inventory/suppliers/paid${selectedStore ? `?store_id=${selectedStore}` : ''}`
      );
      setTotalPaid(paidRes.data.suppliers.reduce((sum, s) => sum + (s.amount_due || 0), 0));
      setSuccess('All payments marked as paid');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const indexOfLast  = currentPage * suppliersPerPage;
  const indexOfFirst = indexOfLast - suppliersPerPage;
  const currentSuppliers = suppliers.slice(indexOfFirst, indexOfLast);
  const totalPages = Math.ceil(suppliers.length / suppliersPerPage);

  const paginate = (n) => { if (n >= 1 && n <= totalPages) setCurrentPage(n); };

  return (
    <div className="admin-container">
      <SideBar />

      <div className="main-content">
        <NavBar />

        <div className="page-content">

          {/* ── Alerts ── */}
          {error   && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}
          {loading && <div className="alert alert-info">Loading...</div>}

          {/* ── Page Header ── */}
          <div className="dashboard-header">
            <h1 className="dashboard-title">Payment Tracking</h1>
            <p className="dashboard-subtitle">Manage supplier payments for the current month.</p>
          </div>

          {/* ── Summary Strip ── */}
          <div className="payment-summary-strip">
            <div className="payment-summary-card">
              <div className="payment-summary-label">Total Unpaid</div>
              <div className="payment-summary-value unpaid">{formatCurrency(totalUnpaid)}</div>
            </div>
            <div className="payment-summary-card">
              <div className="payment-summary-label">Total Paid</div>
              <div className="payment-summary-value paid">{formatCurrency(totalPaid)}</div>
            </div>
          </div>

          {/* ── Main Card ── */}
          <div className="card">

            {/* Card header */}
            <div className="card-header">
              <div className="toolbar" style={{ margin: 0 }}>
                <select value={selectedStore} onChange={(e) => setSelectedStore(e.target.value)}>
                  <option value="">All Stores</option>
                  {stores.map((store) => (
                    <option key={store.id} value={store.id}>{store.name}</option>
                  ))}
                </select>
                <button
                  className={`button ${filter === 'paid' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setFilter('paid')}
                >
                  Paid
                </button>
                <button
                  className={`button ${filter === 'unpaid' ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setFilter('unpaid')}
                >
                  Unpaid
                </button>
              </div>
              <div className="search-wrapper">
                <svg className="search-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  placeholder="Search supplier or product..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>

            <p className="text-muted" style={{ marginBottom: '1rem' }}>
              Showing {currentSuppliers.length} of {suppliers.length} suppliers
            </p>

            {/* ── Table ── */}
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th>Product</th>
                    <th>Amount</th>
                    <th>Due Date</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {currentSuppliers.length > 0 ? (
                    currentSuppliers.map((supplier) => (
                      <tr key={supplier.id}>
                        <td style={{ fontWeight: 500 }}>{supplier.supplier_name || 'N/A'}</td>
                        <td>{supplier.product_name || 'N/A'}</td>
                        <td><strong>{formatCurrency(supplier.amount_due)}</strong></td>
                        <td>
                          <span style={{ color: new Date(supplier.due_date) < new Date() ? 'var(--danger)' : 'inherit' }}>
                            {formatDate(supplier.due_date)}
                          </span>
                        </td>
                        <td>
                          <span className={`status-badge ${supplier.payment_status === 'PAID' ? 'badge-success' : 'badge-danger'}`}>
                            {supplier.payment_status}
                          </span>
                        </td>
                        <td>
                          {filter === 'unpaid' && (
                            <button onClick={() => handlePay(supplier.id)} className="button-action btn-action-success">
                              Mark Paid
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="table-empty">No suppliers found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* ── Card Footer ── */}
            <div className="card-footer-row">
              {filter === 'unpaid' && (
                <button className="button btn-primary" onClick={handleMarkAllPaid}>
                  Mark All as Paid
                </button>
              )}
              <div className="pagination">
                <button className="pagination-button" onClick={() => paginate(currentPage - 1)} disabled={currentPage === 1}>
                  ← Previous
                </button>
                {Array.from({ length: totalPages }, (_, i) => (
                  <button
                    key={i + 1}
                    className={`pagination-button ${currentPage === i + 1 ? 'pagination-active' : ''}`}
                    onClick={() => paginate(i + 1)}
                  >
                    {i + 1}
                  </button>
                ))}
                <button className="pagination-button" onClick={() => paginate(currentPage + 1)} disabled={currentPage === totalPages}>
                  Next →
                </button>
              </div>
            </div>

          </div>{/* /card */}
        </div>{/* /page-content */}

        <Footer />
      </div>{/* /main-content */}
    </div>
  );
};

export default Payments;