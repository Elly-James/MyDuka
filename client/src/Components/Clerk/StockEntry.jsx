// src/Components/Clerk/StockEntry.jsx
import React, { useState, useEffect } from 'react';
import { api, handleApiError } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './clerk.css';

const StockEntry = () => {
  const [form, setForm] = useState({
    product_id: '',
    quantity_received: '',
    buying_price: '',
    payment_status: 'unpaid',
    spoilage_count: '0'
  });
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const response = await api.get('/api/products');
        setProducts(response.data.products);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      await api.post('/api/inventory/entries', form);
      setSuccess('Stock entry added successfully');
      // Reset form
      setForm({
        product_id: '',
        quantity_received: '',
        buying_price: '',
        payment_status: 'unpaid',
        spoilage_count: '0'
      });
    } catch (err) {
      handleApiError(err, setError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="clerk-container">
      <SideBar />
      <div className="main-content">
        <NavBar />
        
        {error && <div className="alert error">{error}</div>}
        {success && <div className="alert success">{success}</div>}
        {loading && <div className="loading">Loading products...</div>}

        <h1>Stock Entry</h1>
        
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Product</label>
              <select
                name="product_id"
                value={form.product_id}
                onChange={handleChange}
                required
              >
                <option value="">Select Product</option>
                {products.map(product => (
                  <option key={product.id} value={product.id}>
                    {product.name} (Current: {product.current_stock})
                  </option>
                ))}
              </select>
            </div>
            
            <div className="form-group">
              <label>Quantity Received</label>
              <input
                type="number"
                name="quantity_received"
                value={form.quantity_received}
                onChange={handleChange}
                min="1"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Buying Price (KSh)</label>
              <input
                type="number"
                name="buying_price"
                value={form.buying_price}
                onChange={handleChange}
                min="0"
                step="0.01"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Payment Status</label>
              <select
                name="payment_status"
                value={form.payment_status}
                onChange={handleChange}
                required
              >
                <option value="unpaid">Unpaid</option>
                <option value="paid">Paid</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Spoilage Count (if any)</label>
              <input
                type="number"
                name="spoilage_count"
                value={form.spoilage_count}
                onChange={handleChange}
                min="0"
              />
            </div>
            
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Submitting...' : 'Submit Entry'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default StockEntry;