import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import './merchant.css';

const PaymentTracking = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('unpaid');
  const [currentPage, setCurrentPage] = useState(1);
  const [suppliersPerPage] = useState(4);
  const navigate = useNavigate();

  useEffect(() => {
    fetchUnpaidSuppliers();
  }, []);

  const fetchUnpaidSuppliers = async () => {
    try {
      const response = await api.get('/api/inventory/suppliers/unpaid');
      setSuppliers(response.data.suppliers || []);
      setError('');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handlePay = async (supplierId) => {
    try {
      await api.post(`/api/inventory/suppliers/pay/${supplierId}`);
      fetchUnpaidSuppliers();
      setError('');
    } catch (err) {
      handleApiError(err, setError);
    }
  };

  const handleMarkAllPaid = () => {
    // Implement logic to mark all as paid
    console.log('Mark all as paid');
  };

  // Pagination logic
  const indexOfLastSupplier = currentPage * suppliersPerPage;
  const indexOfFirstSupplier = indexOfLastSupplier - suppliersPerPage;
  const currentSuppliers = suppliers.slice(indexOfFirstSupplier, indexOfLastSupplier);
  const totalPages = Math.ceil(suppliers.length / suppliersPerPage);

  const paginate = (pageNumber) => setCurrentPage(pageNumber);

  return (
    <div className="merchant-container">
      <SideBar />
      <div className="main-content">
        {error && <p className="text-red-500 mb-4">{error}</p>}

        <div className="card">
          <h2 className="card-title">Payment Tracking</h2>
          <div className="flex justify-between items-center mb-4">
            <div className="flex gap-2">
              <div className="text-lg font-semibold">Total Unpaid</div>
              <div className="text-xl font-bold text-red-600">KSh 285,430</div>
              <div className="text-lg font-semibold">Paid This Month</div>
              <div className="text-xl font-bold text-green-600">KSh 324,780</div>
            </div>
            <input
              type="text"
              placeholder="Search supplier..."
              className="p-2 border border-gray-300 rounded-lg w-1/4"
            />
          </div>
          <div className="flex gap-2 mb-4">
            <button
              className={`button ${filter === 'paid' ? 'button-primary' : ''}`}
              onClick={() => setFilter('paid')}
            >
              Paid
            </button>
            <button
              className={`button ${filter === 'unpaid' ? 'button-primary' : ''}`}
              onClick={() => setFilter('unpaid')}
            >
              Unpaid
            </button>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Product</th>
                <th>Amount</th>
                <th>Due Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {currentSuppliers.map((supplier) => (
                <tr key={supplier.id}>
                  <td>{supplier.name}</td>
                  <td>{supplier.product}</td>
                  <td>{supplier.amount_due}</td>
                  <td>
                    <span className={supplier.due_date === 'Overdue' ? 'status-overdue' : ''}>
                      {supplier.due_date}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => handlePay(supplier.id)}
                      className="button button-primary"
                    >
                      ✓
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex justify-between items-center mt-4">
            <button className="button button-primary" onClick={handleMarkAllPaid}>
              Mark All as Paid
            </button>
            <div className="pagination">
              <span>{indexOfFirstSupplier + 1}-{indexOfLastSupplier > suppliers.length ? suppliers.length : indexOfLastSupplier} of {suppliers.length} items</span>
              <button
                className="pagination-button"
                onClick={() => paginate(currentPage - 1)}
                disabled={currentPage === 1}
              >
                &lt;
              </button>
              {Array.from({ length: totalPages }, (_, i) => (
                <button
                  key={i + 1}
                  className={`pagination-button ${currentPage === i + 1 ? 'active' : ''}`}
                  onClick={() => paginate(i + 1)}
                >
                  {i + 1}
                </button>
              ))}
              <button
                className="pagination-button"
                onClick={() => paginate(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                &gt;
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaymentTracking;