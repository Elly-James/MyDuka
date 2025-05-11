// src/Merchant/Dashboard.jsx

import React, { useEffect, useState } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { api, handleApiError, formatCurrency } from '../utils/api';
import useSocket from '../hooks/useSocket';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './merchant.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May'];

const Dashboard = () => {
  const { socket } = useSocket();

  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  const [period, setPeriod] = useState('weekly');

  const [dashboardData, setDashboardData] = useState({
    low_stock_count: 0,
    normal_stock_count: 0,
    total_sales: 0,
    total_spoilage_value: 0,
    unpaid_suppliers_count: 0,
    unpaid_suppliers_amount: 0,
    paid_suppliers_count: 0,
    paid_suppliers_amount: 0,
    low_stock_products: [],
  });

  const [salesData, setSalesData] = useState({ labels: [], datasets: [] });
  const [topProducts, setTopProducts] = useState([]);

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      setError('');
      setSuccess('');

      try {
        // 1) Fetch stores
        const storesResp = await api.get('/api/stores');
        setStores(storesResp.data.stores || []);

        // 2) Dashboard summary
        const sumRes = await api.get(
          `/api/dashboard/summary?period=${period}${selectedStore ? `&store_id=${selectedStore}` : ''}`
        );
        const sum = sumRes.data.data;
        setDashboardData({
          low_stock_count: sum.low_stock_count,
          normal_stock_count: sum.normal_stock_count,
          total_sales: sum.total_sales,
          total_spoilage_value: sum.total_spoilage_value,
          unpaid_suppliers_count: sum.unpaid_suppliers_count,
          unpaid_suppliers_amount: sum.unpaid_suppliers_amount,
          paid_suppliers_count: sum.paid_suppliers_count,
          paid_suppliers_amount: sum.paid_suppliers_amount,
          low_stock_products: sum.low_stock_products || [],
        });

        // 3) Sales chart
        const salesRes = await api.get(
          `/api/reports/sales?period=${period}${selectedStore ? `&store_id=${selectedStore}` : ''}`
        );
        const sData = salesRes.data.data.chart_data;
        const salesLabels = period === 'monthly' ? MONTH_LABELS : sData.labels;
        setSalesData({
          labels: salesLabels,
          datasets: [{
            label: 'Sales (KSh)',
            data: sData.datasets[0]?.data || [],
            backgroundColor: '#6366f1',
            borderColor: '#6366f1',
            borderWidth: 1,
            borderRadius: 4,
            barThickness: period === 'monthly' ? 40 : 20,
          }]
        });

        // 4) Top products
        const topRes = await api.get(
          `/api/reports/top-products?period=${period}${selectedStore ? `&store_id=${selectedStore}` : ''}`
        );
        setTopProducts(topRes.data.top_products || []);

        setSuccess('Dashboard data updated');
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();

    // Socket feedback
    if (socket) {
      socket.on('notification', n => {
        setSuccess(n.message);
        setTimeout(() => setSuccess(''), 4000);
      });
    }
    return () => {
      if (socket) socket.off('notification');
    };
  }, [period, selectedStore, socket]);

  // Build 2-bar chart: Sales + Top Products Avg
  const labels = period === 'monthly' ? MONTH_LABELS : salesData.labels;
  const salesDs = salesData.datasets[0] || { data: labels.map(() => 0) };
  const avg =
    topProducts.length > 0
      ? topProducts.reduce((sum, p) => sum + p.revenue, 0) / topProducts.length
      : 0;
  const avgDs = {
    label: 'Top Products Avg (KSh)',
    data: labels.map(() => avg),
    backgroundColor: '#10b981',
    borderColor: '#10b981',
    borderWidth: 1,
    borderRadius: 4,
    barThickness: period === 'monthly' ? 40 : 20,
  };

  const combinedData = {
    labels,
    datasets: [salesDs, avgDs]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' },
      title: {
        display: true,
        text: `${period.charAt(0).toUpperCase() + period.slice(1)} Performance Overview (${
          selectedStore
            ? stores.find(s => s.id === +selectedStore)?.name
            : 'All Stores'
        })`,
      },
      tooltip: {
        callbacks: {
          label: ctx => `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: 'Amount (KSh)' },
        ticks: {
          // 🔥 Fix: Chart.js v4 passes a tick object; grab .value if present
          callback: val => {
            const num = typeof val === 'object' && val.value != null ? val.value : val;
            return formatCurrency(num);
          }
        }
      },
      x: {
        title: {
          display: true,
          text: period === 'weekly' ? 'Day' : 'Month'
        }
      }
    }
  };

  return (
    <div className="merchant-container flex min-h-screen bg-gray-100">
      <SideBar />
      <div className="main-content flex-1 p-6">
        <NavBar />

        {error && (
          <p className="text-red-500 mb-4 font-bold bg-red-100 p-3 rounded">{error}</p>
        )}
        {success && (
          <p className="text-green-500 mb-4 font-bold bg-green-100 p-3 rounded">{success}</p>
        )}
        {loading && (
          <p className="text-gray-500 bg-gray-100 p-3 rounded">
            Loading dashboard data...
          </p>
        )}

        <div className="dashboard-header mb-6">
          <h1 className="dashboard-title text-3xl font-bold">Morning, Merchant!</h1>
          <p className="dashboard-subtitle text-gray-600">
            Here's what's happening with your stores today.
          </p>
        </div>

        <div className="flex gap-4 mb-6">
          <select
            value={selectedStore}
            onChange={e => setSelectedStore(e.target.value)}
            className="p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Stores</option>
            {stores.map(store => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
          <button
            className={`button px-4 py-2 rounded-lg ${
              period === 'weekly'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
            onClick={() => setPeriod('weekly')}
          >
            Weekly
          </button>
          <button
            className={`button px-4 py-2 rounded-lg ${
              period === 'monthly'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
            onClick={() => setPeriod('monthly')}
          >
            Monthly
          </button>
        </div>

        <div className="dashboard-grid grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="dashboard-metric bg-white p-6 rounded-lg shadow">
            <h3 className="metric-title text-lg font-semibold text-gray-700">
              Unpaid Suppliers
            </h3>
            <p className="metric-value text-2xl font-bold">
              {dashboardData.unpaid_suppliers_count}
            </p>
            <p className="metric-subvalue text-gray-500">
              {formatCurrency(dashboardData.unpaid_suppliers_amount)}
            </p>
          </div>
          <div className="dashboard-metric bg-white p-6 rounded-lg shadow">
            <h3 className="metric-title text-lg font-semibold text-gray-700">
              Paid Suppliers
            </h3>
            <p className="metric-value text-2xl font-bold">
              {dashboardData.paid_suppliers_count}
            </p>
            <p className="metric-subvalue text-gray-500">
              {formatCurrency(dashboardData.paid_suppliers_amount)}
            </p>
          </div>
          <div className="dashboard-metric bg-white p-6 rounded-lg shadow">
            <h3 className="metric-title text-lg font-semibold text-gray-700">
              Low Stock Alerts
            </h3>
            <p
              className={`metric-value text-2xl font-bold ${
                dashboardData.low_stock_count > 0
                  ? 'text-red-600'
                  : 'text-gray-700'
              }`}
            >
              {dashboardData.low_stock_count}
            </p>
          </div>
          <div className="dashboard-metric bg-white p-6 rounded-lg shadow">
            <h3 className="metric-title text-lg font-semibold text-gray-700">
              Normal Stock
            </h3>
            <p className="metric-value text-2xl font-bold">
              {dashboardData.normal_stock_count}
            </p>
          </div>
          <div className="dashboard-metric bg-white p-6 rounded-lg shadow">
            <h3 className="metric-title text-lg font-semibold text-gray-700">
              Total Sales
            </h3>
            <p className="metric-value text-2xl font-bold">
              {formatCurrency(dashboardData.total_sales)}
            </p>
          </div>
          <div className="dashboard-metric bg-white p-6 rounded-lg shadow">
            <h3 className="metric-title text-lg font-semibold text-gray-700">
              Total Spoilage
            </h3>
            <p className="metric-value text-2xl font-bold">
              {formatCurrency(dashboardData.total_spoilage_value)}
            </p>
          </div>
        </div>

        {dashboardData.low_stock_products.length > 0 && (
          <div className="low-stock-alerts mt-6 bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">
              Low Stock Products
            </h3>
            <table className="table w-full border-collapse">
              <thead>
                <tr className="bg-gray-200">
                  <th className="p-3 text-left">Product</th>
                  <th className="p-3 text-left">Current Stock</th>
                  <th className="p-3 text-left">Min Stock Level</th>
                </tr>
              </thead>
              <tbody>
                {dashboardData.low_stock_products.map((p, i) => (
                  <tr
                    key={i}
                    className={i % 2 === 0 ? 'bg-gray-50' : 'bg-white'}
                  >
                    <td className="p-3">{p.name}</td>
                    <td className="p-3">{p.current_stock}</td>
                    <td className="p-3">{p.min_stock_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="dashboard-chart bg-white p-6 rounded-lg shadow mt-6">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">
            Performance Chart
          </h3>
          <div className="chart-container h-96">
            {combinedData.labels.length > 0 ? (
              <Bar data={combinedData} options={chartOptions} />
            ) : (
              <p className="text-gray-500">
                No data available for the selected period/store.
              </p>
            )}
          </div>
        </div>

        <div className="top-products mt-6 bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold text-gray-700 mb-4">
            {selectedStore ? 'Top 5 Selling Products' : 'Top Selling Products'}
          </h3>
          <table className="table w-full border-collapse">
            <thead>
              <tr className="bg-gray-200">
                <th className="p-3 text-left">Product</th>
                <th className="p-3 text-left">Units Sold</th>
                <th className="p-3 text-left">Revenue (KSh)</th>
                <th className="p-3 text-left">Unit Price (KSh)</th>
              </tr>
            </thead>
            <tbody>
              {topProducts.length > 0 ? (
                topProducts.map((prod, idx) => (
                  <tr
                    key={idx}
                    className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}
                  >
                    <td className="p-3">{prod.product_name}</td>
                    <td className="p-3">{prod.units_sold}</td>
                    <td className="p-3">{formatCurrency(prod.revenue)}</td>
                    <td className="p-3">{formatCurrency(prod.unit_price)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan="4"
                    className="text-center text-gray-500 p-3"
                  >
                    No top-selling products found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
