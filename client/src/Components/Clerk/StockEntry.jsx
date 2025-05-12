import React, { useState, useEffect, useContext } from 'react';
import { api, handleApiError } from '../utils/api';
import { AuthContext } from '../context/AuthContext';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './clerk.css';

const StockEntry = () => {
  const { user } = useContext(AuthContext);
  const [form, setForm] = useState({
    product_id: '',
    quantity_received: '',
    buying_price: '',
    selling_price: '',
    payment_status: 'UNPAID',
    quantity_spoiled: '0',
    due_date: '',
  });
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const productsResponse = await api.get('/api/inventory/products');
        setProducts(productsResponse.data.products || []);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm({ ...form, [name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const payload = {
        product_id: parseInt(form.product_id, 10),
        quantity_received: parseInt(form.quantity_received, 10),
        buying_price: parseFloat(form.buying_price),
        selling_price: parseFloat(form.selling_price),
        payment_status: form.payment_status.toUpperCase(),
        quantity_spoiled: parseInt(form.quantity_spoiled, 10),
        store_id: user.store?.id, // Access store_id from user.store.id
        recorded_by: user.id,     // Use user.id
      };
      if (form.due_date) {
        payload.due_date = new Date(form.due_date).toISOString();
      }

      await api.post('/api/inventory/entries', payload);
      setSuccess('Stock entry added successfully');
      setForm({
        product_id: '',
        quantity_received: '',
        buying_price: '',
        selling_price: '',
        payment_status: 'UNPAID',
        quantity_spoiled: '0',
        due_date: '',
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
        {loading && <div className="loading">Loading data...</div>}
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
                {products.map((product) => (
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
              <label>Selling Price (KSh)</label>
              <input
                type="number"
                name="selling_price"
                value={form.selling_price}
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
                <option value="UNPAID">Unpaid</option>
                <option value="PAID">Paid</option>
              </select>
            </div>
            <div className="form-group">
              <label>Quantity Spoiled (if any)</label>
              <input
                type="number"
                name="quantity_spoiled"
                value={form.quantity_spoiled}
                onChange={handleChange}
                min="0"
              />
            </div>
            <div className="form-group">
              <label>Due Date (Optional)</label>
              <input
                type="datetime-local"
                name="due_date"
                value={form.due_date}
                onChange={handleChange}
              />
            </div>
            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
            >
              {loading ? 'Submitting...' : 'Submit Entry'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default StockEntry;