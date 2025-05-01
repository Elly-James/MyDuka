import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import './admin.css';

const Payments = () => {
  const [payments, setPayments] = useState([]);
  const [activeTab, setActiveTab] = useState('unpaid');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(true);
  const [totalUnpaid, setTotalUnpaid] = useState(0);
  const [totalPaid, setTotalPaid] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const itemsPerPage = 5;

  const { token } = useAuth();

  useEffect(() => {
    fetchPayments();
  }, [activeTab, currentPage, searchTerm]);

  const fetchPayments = async () => {
    setLoading(true);
    try {
      // In a real implementation, you would call your API endpoint
      // const response = await axios.get(`/api/payments?status=${activeTab}&page=${currentPage}&search=${searchTerm}`, {
      //   headers: { Authorization: `Bearer ${token}` }
      // });
      
      // For demonstration, using mock data similar to the image
      const mockData = {
        data: [
          { 
            id: 1, 
            supplier: 'Majani Suppliers', 
            product: 'Rice (5kg bags)', 
            amount: 45000, 
            dueDate: '2025-04-25', 
            status: 'unpaid' 
          },
          { 
            id: 2, 
            supplier: 'Kaka Oil Dist.', 
            product: 'Cooking Oil (2L)', 
            amount: 36000, 
            dueDate: '2025-04-30', 
            status: 'unpaid' 
          },
          { 
            id: 3, 
            supplier: 'Sweet Sugar Co.', 
            product: 'Sugar (1kg packs)', 
            amount: 64620, 
            dueDate: '2025-04-15', 
            status: 'unpaid',
            overdue: true
          },
        ],
        meta: {
          total: 14,
          unpaidTotal: 145620,
          paidTotal: 273450
        }
      };

      // Filter based on activeTab
      const filteredData = mockData.data.filter(payment => 
        payment.status === activeTab && 
        (searchTerm === '' || payment.supplier.toLowerCase().includes(searchTerm.toLowerCase()))
      );

      setPayments(filteredData);
      setTotalItems(mockData.meta.total);
      setTotalUnpaid(mockData.meta.unpaidTotal);
      setTotalPaid(mockData.meta.paidTotal);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching payments:', error);
      setLoading(false);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setCurrentPage(1);
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const markAsPaid = async (id) => {
    try {
      // In real implementation, you would call your API
      // await axios.put(`/api/payments/${id}/mark-paid`, {}, {
      //   headers: { Authorization: `Bearer ${token}` }
      // });
      
      // For demonstration, update the local state
      const updatedPayments = payments.filter(payment => payment.id !== id);
      setPayments(updatedPayments);
      
      // Refetch to update the counts
      fetchPayments();
    } catch (error) {
      console.error('Error marking payment as paid:', error);
    }
  };

  const markAllPaid = async () => {
    try {
      // In real implementation, you would call your API
      // await axios.put('/api/payments/mark-all-paid', {}, {
      //   headers: { Authorization: `Bearer ${token}` }
      // });
      
      // For demonstration, clear all current items
      setPayments([]);
      
      // Refetch to update the counts
      fetchPayments();
    } catch (error) {
      console.error('Error marking all payments as paid:', error);
    }
  };

  const formatCurrency = (amount) => {
    return `KSh ${amount.toLocaleString()}`;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const month = date.toLocaleString('default', { month: 'short' });
    const day = date.getDate();
    
    // Check if date is past due
    const isPastDue = date < new Date();
    
    if (isPastDue) {
      return <span className="text-red-500 font-medium">Overdue</span>;
    }
    
    return `${month} ${day}`;
  };

  const totalPages = Math.ceil(totalItems / itemsPerPage);

  return (
    <div className="payment-tracking-container">
      <h1 className="page-title">Payment Tracking</h1>
      
      <div className="summary-cards">
        <div className="summary-card">
          <h3 className="card-title">Total Unpaid</h3>
          <p className="amount unpaid">{formatCurrency(totalUnpaid)}</p>
        </div>
        
        <div className="summary-card">
          <h3 className="card-title">Paid This Month</h3>
          <p className="amount paid">{formatCurrency(totalPaid)}</p>
        </div>
      </div>
      
      <div className="payment-controls">
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'paid' ? 'active' : ''}`}
            onClick={() => handleTabChange('paid')}
          >
            Paid
          </button>
          <button 
            className={`tab ${activeTab === 'unpaid' ? 'active' : ''}`}
            onClick={() => handleTabChange('unpaid')}
          >
            Unpaid
          </button>
        </div>
        
        <div className="search-container">
          <input
            type="text"
            placeholder="🔍 Search supplier..."
            value={searchTerm}
            onChange={handleSearch}
            className="search-input"
          />
        </div>
      </div>
      
      {loading ? (
        <p className="loading">Loading payments...</p>
      ) : (
        <>
          <table className="payments-table">
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Product</th>
                <th>Amount</th>
                <th>Due Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((payment) => (
                <tr key={payment.id}>
                  <td>{payment.supplier}</td>
                  <td>{payment.product}</td>
                  <td>{formatCurrency(payment.amount)}</td>
                  <td className={payment.overdue ? 'overdue' : ''}>
                    {formatDate(payment.dueDate)}
                  </td>
                  <td>
                    <button 
                      className="action-button mark-paid"
                      onClick={() => markAsPaid(payment.id)}
                    >
                      ✓
                    </button>
                  </td>
                </tr>
              ))}
              {payments.length === 0 && (
                <tr>
                  <td colSpan="5" className="no-data">
                    No {activeTab} payments found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          
          {activeTab === 'unpaid' && payments.length > 0 && (
            <div className="mark-all-container">
              <button 
                className="mark-all-button"
                onClick={markAllPaid}
              >
                Mark All as Paid
              </button>
            </div>
          )}
          
          {totalItems > itemsPerPage && (
            <div className="pagination">
              <span className="page-info">
                {`${(currentPage - 1) * itemsPerPage + 1}-${Math.min(currentPage * itemsPerPage, totalItems)} of ${totalItems} items`}
              </span>
              <button 
                className="page-nav prev"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              >
                ◄
              </button>
              <button className="page-number active">1</button>
              <button className="page-number">2</button>
              <button 
                className="page-nav next"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              >
                ►
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Payments;