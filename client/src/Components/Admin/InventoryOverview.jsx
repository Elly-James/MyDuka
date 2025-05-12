// src/Components/Admin/InventoryOverview.jsx
import React, { useState, useEffect } from 'react';
import { api, handleApiError, formatCurrency } from '../utils/api';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './admin.css';

const InventoryOverview = () => {
  const [inventory, setInventory] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [categories, setCategories] = useState(['All']);
  const [category, setCategory] = useState('All');
  const [status, setStatus] = useState('All');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchInventory = async () => {
      try {
        const response = await api.get('/api/inventory');
        const data = response.data.inventory;
        
        setInventory(data);
        setFiltered(data);
        
        // Extract unique categories
        const uniqueCategories = ['All', ...new Set(data.map(item => item.category || 'Uncategorized'))];
        setCategories(uniqueCategories);
        
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchInventory();
  }, []);

  useEffect(() => {
    const filteredList = inventory.filter(item => {
      const matchSearch = item.product_name.toLowerCase().includes(search.toLowerCase());
      const matchStatus = status === 'All' || item.payment_status === status;
      const matchCategory = category === 'All' || item.category === category;
      return matchSearch && matchStatus && matchCategory;
    });
    setFiltered(filteredList);
  }, [search, status, category, inventory]);

  return (
    <div className="admin-container">
      <SideBar />
      <div className="main-content">
        <NavBar />
        
        {error && <div className="alert error">{error}</div>}
        {loading && <div className="loading">Loading inventory...</div>}

        <h1>Inventory Overview</h1>
        
        <div className="filters">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {categories.map((cat, idx) => (
              <option key={idx} value={cat}>{cat}</option>
            ))}
          </select>
          
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="All">All Status</option>
            <option value="paid">Paid</option>
            <option value="unpaid">Unpaid</option>
          </select>
          
          <input
            type="text"
            placeholder="Search products..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Stock</th>
                <th>Spoilage Rate</th>
                <th>Price</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.product_name}</td>
                  <td className={item.quantity_left <= 10 ? 'text-danger' : ''}>
                    {item.quantity_left}
                  </td>
                  <td>{item.spoilage_rate || '0%'}</td>
                  <td>{formatCurrency(item.unit_price)}</td>
                  <td>
                    <span className={`badge ${item.payment_status === 'paid' ? 'success' : 'warning'}`}>
                      {item.payment_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default InventoryOverview;