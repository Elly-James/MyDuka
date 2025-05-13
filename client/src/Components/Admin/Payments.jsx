import React, { useState, useEffect } from 'react';
import { api, formatCurrency, formatDate, handleApiError } from '../utils/api';
import useSocket from '../hooks/useSocket';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
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
          `/api/inventory/suppliers/${filter}${
            selectedStore ? `?store_id=${selectedStore}` : ''
          }${searchTerm ? `${selectedStore ? '&' : '?'}search=${encodeURIComponent(searchTerm)}` : ''}`
        );
        setSuppliers(suppliersResponse.data.suppliers || []);
        const unpaidResponse = await api.get(
          `/api/inventory/suppliers/unpaid${selectedStore ? `?store_id=${selectedStore}` : ''}`
        );
        const unpaidTotal = unpaidResponse.data.suppliers.reduce(
          (sum, s) => sum + (s.amount_due || 0),
          0
        );
        setTotalUnpaid(unpaidTotal);
        const paidResponse = await api.get(
          `/api/inventory/suppliers/paid${selectedStore ? `?store_id=${selectedStore}` : ''}`
        );
        const paidTotal = paidResponse.data.suppliers.reduce(
          (sum, s) => sum + (s.amount_due || 0),
          0
        );
        setTotalPaid(paidTotal);
        setSuccess('Payment data loaded successfully');
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    if (socket && typeof socket.on === 'function') {
      socket.on('payment_updated', () => {
        setSuccess('Payment status updated');
        fetchData();
      });
      socket.on('notification', (notification) => {
        setSuccess(notification.message);
      });
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
      setSuppliers(
        suppliers.map((s) => (s.id === entryId ? { ...s, payment_status: 'PAID' } : s))
      );
      setSuccess('Payment marked as paid');
      const unpaidResponse = await api.get(
        `/api/inventory/suppliers/unpaid${selectedStore ? `?store_id=${selectedStore}` : ''}`
      );
      const paidResponse = await api.get(
        `/api/inventory/suppliers/paid${selectedStore ? `?store_id=${selectedStore}` : ''}`
      );
      setTotalUnpaid(unpaidResponse.data.suppliers.reduce(
        (sum, s) => sum + (s.amount_due || 0),
        0
      ));
      setTotalPaid(paidResponse.data.suppliers.reduce(
        (sum, s) => sum + (s.amount_due || 0),
        0
      ));
      setError('');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handleMarkAllPaid = async () => {
    try {
      const unpaidEntries = suppliers
        .filter((s) => s.payment_status === 'UNPAID')
        .map((s) => s.id);
      await Promise.all(unpaidEntries.map((id) => api.put(`/api/inventory/update-payment/${id}`)));
      setSuppliers(
        suppliers.map((s) => (unpaidEntries.includes(s.id) ? { ...s, payment_status: 'PAID' } : s))
      );
      setTotalUnpaid(0);
      const paidResponse = await api.get(
        `/api/inventory/suppliers/paid${selectedStore ? `?store_id=${selectedStore}` : ''}`
      );
      setTotalPaid(paidResponse.data.suppliers.reduce(
        (sum, s) => sum + (s.amount_due || 0),
        0
      ));
      setSuccess('All payments marked as paid');
      setError('');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const indexOfLastSupplier = currentPage * suppliersPerPage;
  const indexOfFirstSupplier = indexOfLastSupplier - suppliersPerPage;
  const currentSuppliers = suppliers.slice(indexOfFirstSupplier, indexOfLastSupplier);
  const totalPages = Math.ceil(suppliers.length / suppliersPerPage);

  const paginate = (pageNumber) => {
    if (pageNumber >= 1 && pageNumber <= totalPages) {
      setCurrentPage(pageNumber);
    }
  };

  return (
    <div className="admin-container flex min-h-screen bg-gray-100">
      <SideBar />
      <div className="main-content flex-1 p-6 max-w-full">
        <NavBar />
        {error && <p className="text-red-500 mb-4 font-bold bg-red-100 p-3 rounded">{error}</p>}
        {success && <p className="text-green-500 mb-4 font-bold bg-green-100 p-3 rounded">{success}</p>}
        {loading && <p className="text-gray-500 bg-gray-100 p-3 rounded">Loading...</p>}

        <div className="dashboard-header mb-6">
          <h1 className="dashboard-title text-3xl font-bold text-gray-800">Payment Tracking</h1>
          <p className="dashboard-subtitle text-gray-600">Manage supplier payments for your stores.</p>
        </div>

        <div className="card bg-white p-6 rounded-lg shadow">
          <div className="flex justify-between items-center mb-6">
            <div className="flex gap-4">
              <select
                value={selectedStore}
                onChange={(e) => setSelectedStore(e.target.value)}
                className="p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All Stores</option>
                {stores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="unpaid">Unpaid</option>
                <option value="paid">Paid</option>
                <option value="all">All</option>
              </select>
              <input
                type="text"
                placeholder="Search suppliers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            {filter === 'unpaid' && (
              <button
                onClick={handleMarkAllPaid}
                className="button px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
              >
                Mark All Paid
              </button>
            )}
          </div>

          <div className="summary-table mb-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">Payment Summary</h3>
            <table className="table w-full border-collapse">
              <thead>
                <tr className="bg-gray-200">
                  <th className="p-3 text-left text-gray-700">Metric</th>
                  <th className="p-3 text-left text-gray-700">Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-3">Total Unpaid</td>
                  <td className="p-3">{formatCurrency(totalUnpaid)}</td>
                </tr>
                <tr>
                  <td className="p-3">Total Paid</td>
                  <td className="p-3">{formatCurrency(totalPaid)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="overflow-x-auto">
            <table className="table w-full border-collapse">
              <thead>
                <tr className="bg-gray-200">
                  <th className="p-3 text-left text-gray-700">Supplier</th>
                  <th className="p-3 text-left text-gray-700">Product</th>
                  <th className="p-3 text-left text-gray-700">Amount Due</th>
                  <th className="p-3 text-left text-gray-700">Due Date</th>
                  <th className="p-3 text-left text-gray-700">Status</th>
                  <th className="p-3 text-left text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {currentSuppliers.length > 0 ? (
                  currentSuppliers.map((supplier) => (
                    <tr key={supplier.id} className="border-b hover:bg-gray-50">
                      <td className="p-3">{supplier.supplier_name || 'N/A'}</td>
                      <td className="p-3">{supplier.product_name || 'N/A'}</td>
                      <td className="p-3">{formatCurrency(supplier.amount_due)}</td>
                      <td className="p-3">{formatDate(supplier.due_date)}</td>
                      <td className="p-3">
                        <span
                          className={`status-badge px-2 py-1 rounded-full text-sm ${
                            supplier.payment_status === 'PAID'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {supplier.payment_status}
                        </span>
                      </td>
                      <td className="p-3">
                        {supplier.payment_status === 'UNPAID' && (
                          <button
                            onClick={() => handlePay(supplier.id)}
                            className="button-action px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                          >
                            Mark Paid
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="6" className="text-center text-gray-500 p-3">
                      No suppliers found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between items-center mt-4">
            <button
              className="pagination-button px-3 py-1 rounded-lg bg-gray-200 text-gray-700 disabled:opacity-50"
              onClick={() => paginate(currentPage - 1)}
              disabled={currentPage === 1}
            >
              Previous
            </button>
            <div className="flex gap-2">
              {Array.from({ length: totalPages }, (_, i) => (
                <button
                  key={i + 1}
                  className={`pagination-button px-3 py-1 rounded-lg ${
                    currentPage === i + 1
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-200 text-gray-700'
                  }`}
                  onClick={() => paginate(i + 1)}
                >
                  {i + 1}
                </button>
              ))}
            </div>
            <button
              className="pagination-button px-3 py-1 rounded-lg bg-gray-200 text-gray-700 disabled:opacity-50"
              onClick={() => paginate(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Payments;