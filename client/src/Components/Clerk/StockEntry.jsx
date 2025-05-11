import React, { useState } from 'react';
import axios from 'axios';

// StockEntry component that allows the clerks to submit new inventory entries
const StockEntry = () => {
  const [form, setForm] = useState({
    product_name: '',
    quantity: '',
    price: '',
    payment_status: '',
    spoilage_count: '',
  });

  // This Updates the form state in the input fields as the user types 
  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  // This Handles the form submission
  const handleSubmit = async (e) => {
    e.preventDefault(); 

    try {
      // Getting the token from localStorage for authentication
      const token = localStorage.getItem('token');

      // Sending a POST request to the backend with the form data
      await axios.post(
        'http://localhost:5000/api/inventory/entries',
        form,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // If it is successful, show a success message and then reset the form
      alert('Stock entry added successfully');
      setForm({ 
        product_name: '', 
        quantity: '', 
        price: '', 
        payment_status: '', 
        spoilage_count: '' 
      });

    } catch (err) {
      // If there is an error, show the error alert 
      alert('Error submitting entry');
      console.error(err);
    }
  };

  // JSX returned by the component
  return (
    <div>
      <h2>Add Stock Entry</h2>

      {/* Form for submitting stock entry */}
      <form onSubmit={handleSubmit}>
        
        {/* Product Name Input */}
        <input
          type="text"
          name="product_name"
          placeholder="Product Name"
          value={form.product_name}
          onChange={handleChange}
          required
        />

        {/* The Quantity Input */}
        <input
          type="number"
          name="quantity"
          placeholder="Quantity Received"
          value={form.quantity}
          onChange={handleChange}
          required
        />

        {/* The Price Input */}
        <input
          type="number"
          name="price"
          placeholder="Price (KSh)"
          value={form.price}
          onChange={handleChange}
          required
        />

        {/* Dropdown for Payment Status  */}
        <select
          name="payment_status"
          value={form.payment_status}
          onChange={handleChange}
          required
        >
          <option value="">Select status</option>
          <option value="PAID">Paid</option>
          <option value="UNPAID">Unpaid</option>
        </select>

        {/* The Spoilage Count Input */}
        <input
          type="number"
          name="spoilage_count"
          placeholder="Spoilage Count"
          value={form.spoilage_count}
          onChange={handleChange}
        />

        {/* The Submit Button */}
        <button type="submit">Submit</button>
      </form>
    </div>
  );
};

export default StockEntry;
