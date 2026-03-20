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
import Footer from '../Footer/Footer';

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
            backgroundColor: '#d4a853',
            borderColor: '#d4a853',
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
        setTimeout(() => setSuccess(''), 3000);
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

  const combinedData = { labels, datasets: [salesDs, avgDs] };

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
    <div className="merchant-container">
      <SideBar />

      <div className="main-content">
        <NavBar />

        <div className="page-content">

          {/* ── Alerts ── */}
          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">{success}</div>}
          {loading && <div className="alert alert-info">Loading dashboard data...</div>}

          {/* ── Page Header ── */}
          <div className="dashboard-header">
            <h1 className="dashboard-title">Good Morning, Merchant!</h1>
            <p className="dashboard-subtitle">
              Here's what's happening with your stores today.
            </p>
          </div>

          {/* ── Toolbar ── */}
          <div className="toolbar">
            <select
              value={selectedStore}
              onChange={e => setSelectedStore(e.target.value)}
            >
              <option value="">All Stores</option>
              {stores.map(store => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>

            <button
              className={`button ${period === 'weekly' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setPeriod('weekly')}
            >
              Weekly
            </button>
            <button
              className={`button ${period === 'monthly' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setPeriod('monthly')}
            >
              Monthly
            </button>
          </div>

          {/* ── Metric Cards ── */}
          <div className="dashboard-grid">
            <div className="dashboard-metric">
              <div className="metric-title">Unpaid Suppliers</div>
              <div className="metric-value">
                {dashboardData.unpaid_suppliers_count}
              </div>
              <div className="metric-subvalue">
                {formatCurrency(dashboardData.unpaid_suppliers_amount)}
              </div>
            </div>

            <div className="dashboard-metric">
              <div className="metric-title">Paid Suppliers</div>
              <div className="metric-value">
                {dashboardData.paid_suppliers_count}
              </div>
              <div className="metric-subvalue">
                {formatCurrency(dashboardData.paid_suppliers_amount)}
              </div>
            </div>

            <div className="dashboard-metric">
              <div className="metric-title">Low Stock Alerts</div>
              <div className={`metric-value ${dashboardData.low_stock_count > 0 ? 'metric-danger' : ''}`}>
                {dashboardData.low_stock_count}
              </div>
            </div>

            <div className="dashboard-metric">
              <div className="metric-title">Normal Stock</div>
              <div className="metric-value">
                {dashboardData.normal_stock_count}
              </div>
            </div>

            <div className="dashboard-metric">
              <div className="metric-title">Total Sales</div>
              <div className="metric-value metric-currency">
                {formatCurrency(dashboardData.total_sales)}
              </div>
            </div>

            <div className="dashboard-metric">
              <div className="metric-title">Total Spoilage</div>
              <div className="metric-value metric-currency">
                {formatCurrency(dashboardData.total_spoilage_value)}
              </div>
            </div>
          </div>

          {/* ── Low Stock Products ── */}
          {dashboardData.low_stock_products.length > 0 && (
            <div className="low-stock-alerts">
              <h3 className="section-title">⚠ Low Stock Products</h3>
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Current Stock</th>
                      <th>Min Stock Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardData.low_stock_products.map((p, i) => (
                      <tr key={i}>
                        <td>{p.name}</td>
                        <td>
                          <span className="badge badge-danger">{p.current_stock}</span>
                        </td>
                        <td>{p.min_stock_level}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Performance Chart ── */}
          <div className="dashboard-chart">
            <div className="chart-header">
              <h3 className="chart-title">Performance Chart</h3>
            </div>
            <div className="chart-container">
              {combinedData.labels.length > 0 ? (
                <Bar data={combinedData} options={chartOptions} />
              ) : (
                <p className="text-muted">
                  No data available for the selected period/store.
                </p>
              )}
            </div>
          </div>

          {/* ── Top Products ── */}
          <div className="top-products">
            <h3 className="section-title">
              {selectedStore ? 'Top 5 Selling Products' : 'Top Selling Products'}
            </h3>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Units Sold</th>
                    <th>Revenue (KSh)</th>
                    <th>Unit Price (KSh)</th>
                  </tr>
                </thead>
                <tbody>
                  {topProducts.length > 0 ? (
                    topProducts.map((prod, idx) => (
                      <tr key={idx}>
                        <td>{prod.product_name}</td>
                        <td>{prod.units_sold}</td>
                        <td>{formatCurrency(prod.revenue)}</td>
                        <td>{formatCurrency(prod.unit_price)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" className="table-empty">
                        No top-selling products found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>{/* /page-content */}
        <Footer />
      </div>{/* /main-content */}
    </div>
  );
};

export default Dashboard;