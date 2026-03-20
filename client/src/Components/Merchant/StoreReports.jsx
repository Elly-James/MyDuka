import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { fetchSalesReport, fetchTopProducts } from '../store/slices/reportSlice';
import { api, formatCurrency, handleApiError } from '../utils/api';
import { jsPDF } from 'jspdf';
import useSocket from '../hooks/useSocket';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import Footer from '../Footer/Footer';
import './merchant.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May'];

const StoreReports = () => {
  const dispatch = useDispatch();
  const { salesReport, topProducts, loading: reduxLoading, error: reduxError } = useSelector(
    (state) => state.reports
  );
  const [period, setPeriod] = useState('weekly');
  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState('');
  const [dashboardData, setDashboardData] = useState({
    total_sales: 0,
    total_spoilage_value: 0,
    paid_suppliers_count: 0,
    paid_suppliers_amount: 0,
    unpaid_suppliers_count: 0,
    unpaid_suppliers_amount: 0,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { socket } = useSocket();

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError('');
      try {
        // Fetch stores
        const storesResponse = await api.get('/api/stores');
        setStores(storesResponse.data.stores || []);

        // Fetch dashboard summary (mimicking Dashboard.jsx)
        const sumRes = await api.get(
          `/api/dashboard/summary?period=${period}${selectedStore ? `&store_id=${selectedStore}` : ''}`
        );
        console.log('Dashboard Summary Response:', sumRes.data); // Debug log
        const sum = sumRes.data.data || {
          total_sales: 0,
          total_spoilage_value: 0,
          paid_suppliers_count: 0,
          paid_suppliers_amount: 0,
          unpaid_suppliers_count: 0,
          unpaid_suppliers_amount: 0,
        };
        setDashboardData({
          total_sales: sum.total_sales,
          total_spoilage_value: sum.total_spoilage_value,
          paid_suppliers_count: sum.paid_suppliers_count,
          paid_suppliers_amount: sum.paid_suppliers_amount,
          unpaid_suppliers_count: sum.unpaid_suppliers_count,
          unpaid_suppliers_amount: sum.unpaid_suppliers_amount,
        });

        setSuccess('Data loaded successfully');
        setTimeout(() => setSuccess(''), 3000);
      } catch (err) {
        handleApiError(err, setError);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    dispatch(fetchSalesReport({ period, store_id: selectedStore || undefined }));
    dispatch(fetchTopProducts({ period, store_id: selectedStore || undefined }));

    if (socket) {
      socket.on('report_updated', () => {
        setSuccess('Report data updated');
        fetchData();
        dispatch(fetchSalesReport({ period, store_id: selectedStore || undefined }));
        dispatch(fetchTopProducts({ period, store_id: selectedStore || undefined }));
      });
      socket.on('notification', (notification) => {
        setSuccess(notification.message);
        setTimeout(() => setSuccess(''), 4000);
      });
    }

    return () => {
      if (socket) {
        socket.off('report_updated');
        socket.off('notification');
      }
    };
  }, [dispatch, period, selectedStore, socket]);

  const exportToPDF = () => {
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.text('Store Reports', 20, 20);
    doc.setFontSize(12);
    doc.text(`Period: ${period.charAt(0).toUpperCase() + period.slice(1)}`, 20, 30);
    doc.text(
      `Store: ${stores.find((s) => s.id === parseInt(selectedStore))?.name || 'All Stores'}`,
      20,
      40
    );
    doc.text(`Generated: ${new Date().toLocaleDateString()}`, 20, 50);
    doc.setFontSize(14);
    doc.text('Summary', 20, 60);
    doc.setFontSize(12);
    doc.text(`Total Sales: ${formatCurrency(dashboardData.total_sales)}`, 20, 70);
    doc.text(`Total Spoilage: ${formatCurrency(dashboardData.total_spoilage_value)}`, 20, 80);
    doc.text(
      `Paid Suppliers: ${dashboardData.paid_suppliers_count} (${formatCurrency(
        dashboardData.paid_suppliers_amount
      )})`,
      20,
      90
    );
    doc.text(
      `Unpaid Suppliers: ${dashboardData.unpaid_suppliers_count} (${formatCurrency(
        dashboardData.unpaid_suppliers_amount
      )})`,
      20,
      100
    );
    doc.setFontSize(14);
    doc.text('Top Selling Products', 20, 110);
    doc.setFontSize(12);
    topProducts.forEach((product, index) => {
      doc.text(
        `${index + 1}. ${product.product_name}: ${product.units_sold} units, ${formatCurrency(
          product.revenue
        )}, Growth: ${product.growth}%`,
        20,
        120 + index * 10
      );
    });
    doc.save(`store-reports-${period}-${selectedStore || 'all'}-${Date.now()}.pdf`);
  };

  const getChartLabels = () => {
    if (period === 'weekly') {
      return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    }
    return MONTH_LABELS;
  };

  const salesChartData = {
    labels: salesReport?.chart_data?.labels || getChartLabels(),
    datasets: [
      {
        label: 'Sales (KSh)',
        data: salesReport?.chart_data?.datasets?.[0]?.data || getChartLabels().map(() => 0),
        borderColor: '#d4a853',
        backgroundColor: 'rgba(212, 168, 83, 0.15)',
        tension: 0.4,
        fill: true,
        pointBackgroundColor: '#d4a853',
        pointRadius: 4,
      },
      {
        label: 'Top Products Avg (KSh)',
        data:
          topProducts.length > 0
            ? getChartLabels().map(
                () => topProducts.reduce((sum, p) => sum + p.revenue, 0) / topProducts.length
              )
            : getChartLabels().map(() => 0),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.15)',
        tension: 0.4,
        fill: true,
        pointBackgroundColor: '#10b981',
        pointRadius: 4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' },
      title: {
        display: true,
        text: `Sales Trend (${
          selectedStore
            ? stores.find((s) => s.id === parseInt(selectedStore))?.name
            : 'All Stores'
        })`,
      },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const value = ctx.parsed.y;
            return `${ctx.dataset.label}: ${isNaN(value) ? 'N/A' : formatCurrency(value)}`;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: { display: true, text: 'Amount (KSh)' },
        ticks: {
          callback: (val) => {
            const num = typeof val === 'object' && val.value != null ? val.value : val;
            return isNaN(num) ? '' : formatCurrency(num);
          },
        },
      },
      x: {
        title: {
          display: true,
          text: period === 'weekly' ? 'Day' : 'Month',
        },
      },
    },
  };

  return (
    <div className="merchant-container">
      <SideBar />

      <div className="main-content">
        <NavBar />

        <div className="page-content">

          {/* ── Alerts ── */}
          {(error || reduxError) && (
            <div className="alert alert-error">{error || reduxError}</div>
          )}
          {success && (
            <div className="alert alert-success">{success}</div>
          )}
          {(loading || reduxLoading) && (
            <div className="alert alert-info">Loading reports...</div>
          )}

          {/* ── Page Header ── */}
          <div className="dashboard-header">
            <h1 className="dashboard-title">Store Reports</h1>
            <p className="dashboard-subtitle">
              Detailed performance metrics for your stores.
            </p>
          </div>

          {/* ── Main Card ── */}
          <div className="card">

            {/* Card header: filters left, export right */}
            <div className="card-header">
              <div className="toolbar" style={{ margin: 0 }}>
                <select
                  value={selectedStore}
                  onChange={(e) => setSelectedStore(e.target.value)}
                >
                  <option value="">All Stores</option>
                  {stores.map((store) => (
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

              <button
                className="button btn-success"
                onClick={exportToPDF}
              >
                ↓ Export PDF
              </button>
            </div>

            {/* ── Sales Trend Chart ── */}
            <div className="dashboard-chart">
              <div className="chart-header">
                <h2 className="chart-title">Sales Trend</h2>
              </div>
              <div className="chart-container">
                <Line data={salesChartData} options={chartOptions} />
              </div>
            </div>

            {/* ── Summary Table ── */}
            <div style={{ marginTop: '2rem' }}>
              <h3 className="section-title">Summary</h3>
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Total Sales</td>
                      <td>
                        <strong>{formatCurrency(dashboardData.total_sales)}</strong>
                      </td>
                    </tr>
                    <tr>
                      <td>Total Spoilage</td>
                      <td>{formatCurrency(dashboardData.total_spoilage_value)}</td>
                    </tr>
                    <tr>
                      <td>Paid Suppliers</td>
                      <td>
                        <span className="badge badge-success">
                          {dashboardData.paid_suppliers_count}
                        </span>
                        &nbsp;({formatCurrency(dashboardData.paid_suppliers_amount)})
                      </td>
                    </tr>
                    <tr>
                      <td>Unpaid Suppliers</td>
                      <td>
                        <span className="badge badge-danger">
                          {dashboardData.unpaid_suppliers_count}
                        </span>
                        &nbsp;({formatCurrency(dashboardData.unpaid_suppliers_amount)})
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* ── Top Products Table ── */}
            <div style={{ marginTop: '2rem' }}>
              <h3 className="section-title">Top Selling Products</h3>
              <div className="table-wrapper">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Units Sold</th>
                      <th>Revenue (KSh)</th>
                      <th>Growth</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topProducts.length > 0 ? (
                      topProducts.map((product, index) => (
                        <tr key={index}>
                          <td>{product.product_name}</td>
                          <td>{product.units_sold}</td>
                          <td>{formatCurrency(product.revenue)}</td>
                          <td>
                            <span
                              className={`badge ${
                                product.growth > 0 ? 'badge-success' : 'badge-danger'
                              }`}
                            >
                              {product.growth > 0 ? '+' : ''}{product.growth}%
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="4" className="table-empty">
                          No products found
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>{/* /card */}
        </div>{/* /page-content */}
        <Footer />
      </div>{/* /main-content */}
    </div>
  );
};

export default StoreReports;