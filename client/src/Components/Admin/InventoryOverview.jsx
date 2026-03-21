import React, { useState, useEffect, useMemo } from 'react';
import { api, handleApiError, formatCurrency } from '../utils/api';
import useSocket from '../hooks/useSocket';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import Footer from '../Footer/Footer';
import './admin.css';

const InventoryOverview = () => {
  const [inventory, setInventory] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [categories, setCategories] = useState(['All Categories']);
  const [category, setCategory] = useState('All Categories');
  const [paymentStatus, setPaymentStatus] = useState('All');
  const [search, setSearch] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { socket } = useSocket();

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [productsResponse, entriesResponse] = await Promise.all([
          api.get('/api/inventory/products', { params: { per_page: 100 } }),
          api.get('/api/inventory/entries', { params: { per_page: 500 } }),
        ]);
        const productsData = productsResponse.data.products || [];
        const entriesData  = entriesResponse.data.entries || [];

        const productsWithSpoilage = productsData.map((product) => {
          const productEntries  = entriesData.filter((e) => e.product_id === product.id);
          const totalReceived   = productEntries.reduce((sum, e) => sum + e.quantity_received, 0);
          const totalSpoiled    = productEntries.reduce((sum, e) => sum + e.quantity_spoiled, 0);
          const rawStatus       = productEntries.length > 0 ? productEntries[0].payment_status : 'UNPAID';
          return {
            ...product,
            spoilage_percentage: totalReceived > 0 ? (totalSpoiled / totalReceived * 100) : 0,
            payment_status: rawStatus.replace('PaymentStatus.', ''),
          };
        });

        const uniqueCategories = [
          'All Categories',
          ...new Set(productsData.map((p) => p.category_name || 'Uncategorized').filter(Boolean)),
        ];

        setInventory(productsWithSpoilage);
        setFiltered(productsWithSpoilage);
        setCategories(uniqueCategories);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    if (!socket) return;
    const handleStockUpdate = (data) => {
      setInventory((prev) =>
        prev.map((item) =>
          item.id === data.product_id
            ? { ...item, current_stock: data.current_stock, updated_at: data.updated_at,
                payment_status: data.payment_status ? data.payment_status.replace('PaymentStatus.', '') : item.payment_status }
            : item
        )
      );
    };
    const handleLowStock = (data) => {
      setError(`Low stock alert: ${data.message}`);
      setTimeout(() => setError(''), 5000);
    };
    socket.on('STOCK_UPDATED', handleStockUpdate);
    socket.on('LOW_STOCK', handleLowStock);
    return () => { socket.off('STOCK_UPDATED', handleStockUpdate); socket.off('LOW_STOCK', handleLowStock); };
  }, [socket]);

  useEffect(() => {
    let list = [...inventory];
    if (category !== 'All Categories') list = list.filter((i) => i.category_name === category);
    if (paymentStatus !== 'All')        list = list.filter((i) => i.payment_status === paymentStatus);
    if (search) {
      const s = search.toLowerCase();
      list = list.filter((i) => i.name.toLowerCase().includes(s) || (i.sku && i.sku.toLowerCase().includes(s)));
    }
    if (sortConfig.key) {
      list.sort((a, b) => {
        const av = a[sortConfig.key], bv = b[sortConfig.key];
        if (av == null) return sortConfig.direction === 'asc' ? 1 : -1;
        if (bv == null) return sortConfig.direction === 'asc' ? -1 : 1;
        if (typeof av === 'number') return sortConfig.direction === 'asc' ? av - bv : bv - av;
        return sortConfig.direction === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      });
    }
    setFiltered(list);
    setCurrentPage(1);
  }, [search, category, paymentStatus, inventory, sortConfig]);

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filtered.slice(start, start + itemsPerPage);
  }, [filtered, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filtered.length / itemsPerPage);

  const getStockBadge = (current, min) => {
    if (current <= min)       return 'badge-danger';
    if (current <= min * 1.5) return 'badge-warning';
    return 'badge-success';
  };

  const SortIcon = ({ col }) =>
    sortConfig.key === col ? (
      <span style={{ marginLeft: '0.25rem' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
    ) : null;

  return (
    <div className="admin-container">
      <SideBar />

      <div className="main-content">
        <NavBar />

        <div className="page-content">

          {/* ── Alerts ── */}
          {error && <div className="alert alert-error">{error}</div>}
          {loading && <div className="alert alert-info">Loading inventory...</div>}

          {/* ── Page Header ── */}
          <div className="dashboard-header">
            <h1 className="dashboard-title">Inventory Overview</h1>
            <p className="dashboard-subtitle">Monitor stock levels, spoilage rates and payment status.</p>
          </div>

          {/* ── Main Card ── */}
          <div className="card">

            {/* Filters toolbar */}
            <div className="card-header">
              <div className="toolbar" style={{ margin: 0 }}>
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                  {categories.map((cat, idx) => (
                    <option key={idx} value={cat}>{cat}</option>
                  ))}
                </select>

                <select value={paymentStatus} onChange={(e) => setPaymentStatus(e.target.value)}>
                  <option value="All">All Payments</option>
                  <option value="PAID">Paid</option>
                  <option value="UNPAID">Unpaid</option>
                </select>

                <div className="search-wrapper">
                  <svg className="search-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <input
                    type="text"
                    placeholder="Search by product name or SKU..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
              </div>
              <span className="text-muted">
                Showing {paginatedData.length} of {filtered.length} products
              </span>
            </div>

            {/* ── Table ── */}
            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
                <div style={{
                  width: 48, height: 48, borderRadius: '50%',
                  border: '3px solid var(--slate-200)', borderTopColor: 'var(--gold)',
                  animation: 'spin 0.8s linear infinite',
                }}/>
              </div>
            ) : (
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>
                        Product <SortIcon col="name" />
                      </th>
                      <th onClick={() => handleSort('current_stock')} style={{ cursor: 'pointer' }}>
                        Stock <SortIcon col="current_stock" />
                      </th>
                      <th onClick={() => handleSort('spoilage_percentage')} style={{ cursor: 'pointer' }}>
                        Spoilage <SortIcon col="spoilage_percentage" />
                      </th>
                      <th onClick={() => handleSort('unit_price')} style={{ cursor: 'pointer' }}>
                        Price <SortIcon col="unit_price" />
                      </th>
                      <th onClick={() => handleSort('payment_status')} style={{ cursor: 'pointer' }}>
                        Payment <SortIcon col="payment_status" />
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedData.length > 0 ? (
                      paginatedData.map((item) => (
                        <tr key={item.id}>
                          <td>
                            <div style={{ fontWeight: 500 }}>{item.name}</div>
                            <div className="text-muted" style={{ fontSize: '0.75rem' }}>{item.sku || 'No SKU'}</div>
                          </td>
                          <td>
                            <span className={`status-badge ${getStockBadge(item.current_stock, item.min_stock_level)}`}>
                              {item.current_stock}
                            </span>
                            <span className="text-muted" style={{ marginLeft: '0.375rem', fontSize: '0.75rem' }}>
                              / {item.min_stock_level} min
                            </span>
                          </td>
                          <td>{item.spoilage_percentage.toFixed(2)}%</td>
                          <td>{formatCurrency(item.unit_price)}</td>
                          <td>
                            <span className={`status-badge ${item.payment_status === 'PAID' ? 'badge-success' : 'badge-danger'}`}>
                              {item.payment_status || 'UNPAID'}
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" className="table-empty">No inventory items match your filters</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* ── Pagination ── */}
            {totalPages > 1 && (
              <div className="card-footer-row">
                <span className="text-muted">
                  Page {currentPage} of {totalPages} — {filtered.length} total results
                </span>
                <div className="pagination">
                  <button
                    className="pagination-button"
                    onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                    disabled={currentPage === 1}
                  >
                    ← Previous
                  </button>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pg;
                    if (totalPages <= 5)          pg = i + 1;
                    else if (currentPage <= 3)    pg = i + 1;
                    else if (currentPage >= totalPages - 2) pg = totalPages - 4 + i;
                    else pg = currentPage - 2 + i;
                    return (
                      <button
                        key={pg}
                        className={`pagination-button ${currentPage === pg ? 'pagination-active' : ''}`}
                        onClick={() => setCurrentPage(pg)}
                      >
                        {pg}
                      </button>
                    );
                  })}
                  <button
                    className="pagination-button"
                    onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                    disabled={currentPage === totalPages}
                  >
                    Next →
                  </button>
                </div>
              </div>
            )}

          </div>{/* /card */}
        </div>{/* /page-content */}

        <Footer />
      </div>{/* /main-content */}
    </div>
  );
};

export default InventoryOverview;