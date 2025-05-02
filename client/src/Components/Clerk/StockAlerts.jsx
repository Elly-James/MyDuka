import React, { useEffect, useState } from 'react';
import axios from 'axios';

// This displays the low-stock inventory alerts
const StockAlerts = () => {
  const [alerts, setAlerts] = useState([]); // State that holds the list of low stock alerts

  // It fetchs the data when component mounts
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        // Gets token from the localStorage for authentication
        const token = localStorage.getItem('token');

        // Makes a GET request to fetch low stock items
        const res = await axios.get('http://localhost:5000/api/inventory/low-stock', {
          headers: { Authorization: `Bearer ${token}` },
        });

        // Sets the retrieved alerts 
        setAlerts(res.data);
      } catch (err) {
        console.error('Failed to fetch low stock alerts', err);
      }
    };

    fetchAlerts();
  }, []);

  // The function to handle supply request for specific product
  const requestSupply = async (productId) => {
    try {
      const token = localStorage.getItem('token');

      // A post request supply for a product
      await axios.post(
        'http://localhost:5000/api/inventory/supply-requests',
        { product_id: productId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      alert('Supply request sent');
    } catch (err) {
      alert('Failed to send request');
    }
  };

  // The JSX returned by component
  return (
    <div>
      <h2>Stock Alerts</h2>

      {/* If no alerts available, show the message */}
      {alerts.length === 0 ? (
        <p>No low stock items.</p>
      ) : (
        <ul>
          {/* This Iterates over each alert item and displays it */}
          {alerts.map((item) => (
            <li key={item.id}>
              {/* Displays the product name and quantity */}
              <span>{item.product_name}: Low stock ({item.quantity} left)</span>

              {/* The button that requests more supply */}
              <button onClick={() => requestSupply(item.product_id)}>
                Request Supply
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default StockAlerts;
