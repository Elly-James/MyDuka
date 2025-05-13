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
        // Fetch stores
        const storesResponse = await api.get('/api/stores');
        setStores(storesResponse.data.stores || []);

        // Fetch suppliers
        const suppliersResponse = await api.get(
          `/api/inventory/suppliers/${filter}${
            selectedStore ? `?store_id=${selectedStore}` : ''
          }${searchTerm ? `${selectedStore ? '&' : '?'}search=${encodeURIComponent(searchTerm)}` : ''}`
        );
        setSuppliers(suppliersResponse.data.suppliers || []);

        // Fetch total unpaid
        const unpaidResponse = await api.get(
          `/api/inventory/suppliers/unpaid${selectedStore ? `?store_id=${selectedStore}` : ''}`
        );
        const unpaidTotal = unpaidResponse.data.suppliers.reduce(
          (sum, s) => sum + (s.amount_due || 0),
          0
        );
        setTotalUnpaid(unpaidTotal);

        // Fetch total paid
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
        console.error('Fetch data error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData().catch((err) => {
      console.error('Unhandled fetchData error:', err);
      setError('Failed to load data');
    });

    if (socket && typeof socket.on === 'function') {
      socket.on('payment_updated', () => {
        setSuccess('Payment status updated');
        fetchData().catch((err) => {
          console.error('Payment updated error:', err);
          setError('Failed to refresh payment data');
        });
      });
      socket.on('notification', (notification) => {
        setSuccess(notification.message);
      });
    } else {
      console.warn('Socket is not initialized or invalid');
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
      <div className="main-content flex-1 p-6">
        <NavBar />
        {error && <p className="text-red-500 mb-4 font-bold bg-red-100 p-3 rounded">{error}</p>}
        {success && <p className="text-green-500 mb-4 font-bold bg-green-100 p-3 rounded">{success}</p>}
        {loading && <p className="text-gray-500 bg-gray-100 p-3 rounded">Loading...</p>}

        <div className="dashboard-header mb-6">
          <h1 className="dashboard-title text-3xl font-bold">Payment Tracking</h1>
          <p className="dashboard-subtitle text-gray-600">Manage supplier payments for the current month.</p>
        </div>

        <div className="card bg-white p-6 rounded-lg shadow">
          <div className="flex justify-between items-center mb-4">
            <div className="flex gap-4">
              <div>
                <div className="text-lg font-semibold">Total Unpaid</div>
                <div className="text-xl font-bold text-red-600">{formatCurrency(totalUnpaid)}</div>
              </div>
              <div>
                <div className="text-lg font-semibold">Total Paid</div>
                <div className="text-xl font-bold text-green-600">{formatCurrency(totalPaid)}</div>
              </div>
            </div>
            <input
              type="text"
              placeholder="Search supplier or product..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="p-2 border border-gray-300 rounded-lg w-1/4 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="flex gap-2 mb-4">
            <select
              value={selectedStore}
              onChange={(e) => setSelectedStore(e.target.value)}
              className="p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Stores</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
            <button
              className={`button px-4 py-2 rounded-lg ${filter === 'paid' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'}`}
              onClick={() => setFilter('paid')}
            >
              Paid
            </button>
            <button
              className={`button px-4 py-2 rounded-lg ${filter === 'unpaid' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'}`}
              onClick={() => setFilter('unpaid')}
            >
              Unpaid
            </button>
          </div>
          <div className="mb-4">
            <p className="text-gray-600">Showing {currentSuppliers.length} of {suppliers.length} suppliers</p>
          </div>
          <table className="table w-full mb-6">
            <thead>
              <tr className="bg-gray-200">
                <th className="p-3 text-left">Supplier</th>
                <th className="p-3 text-left">Product</th>
                <th className="p-3 text-left">Amount</th>
                <th className="p-3 text-left">Due Date</th>
                <th className="p-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {currentSuppliers.length > 0 ? (
                currentSuppliers.map((supplier) => (
                  <tr key={supplier.id}>
                    <td className="p-3">{supplier.supplier_name}</td>
                    <td className="p-3">{supplier.product_name}</td>
                    <td className="p-3">{formatCurrency(supplier.amount_due)}</td>
                    <td className="p-3">
                      <span
                        className={
                          new Date(supplier.due_date) < new Date() ? 'text-red-600' : 'text-gray-700'
                        }
                      >
                        {formatDate(supplier.due_date)}
                      </span>
                    </td>
                    <td className="p-3">
                      {filter === 'unpaid' && (
                        <button
                          onClick={() => handlePay(supplier.id)}
                          className="button px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                        >
                          Mark Paid
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="text-center text-gray-500 p-3">No suppliers found</td>
                </tr>
              )}
            </tbody>
          </table>
          <div className="flex justify-between items-center mt-4">
            {filter === 'unpaid' && (
              <button
                className="button px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                onClick={handleMarkAllPaid}
              >
                Mark All as Paid
              </button>
            )}
            <div className="flex justify-between items-center w-full max-w-xs">
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
                      currentPage === i + 1 ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'
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
    </div>
  );
};

export default Payments;