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
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.2)',
        tension: 0.4,
        fill: true,
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
        backgroundColor: 'rgba(16, 185, 129, 0.2)',
        tension: 0.4,
        fill: true,
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
          selectedStore ? stores.find((s) => s.id === parseInt(selectedStore))?.name : 'All Stores'
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
    <div className="merchant-container flex min-h-screen bg-gray-100">
      <SideBar />
      <div className="main-content flex-1 p-6">
        <NavBar />
        {error || reduxError ? (
          <p className="text-red-500 mb-4 font-bold bg-red-100 p-3 rounded">{error || reduxError}</p>
        ) : null}
        {success && (
          <p className="text-green-500 mb-4 font-bold bg-green-100 p-3 rounded">{success}</p>
        )}
        {(loading || reduxLoading) && (
          <p className="text-gray-500 bg-gray-100 p-3 rounded">Loading reports...</p>
        )}

        <div className="dashboard-header mb-6">
          <h1 className="dashboard-title text-3xl font-bold">Store Reports</h1>
          <p className="dashboard-subtitle text-gray-600">Detailed performance metrics for your stores.</p>
        </div>

        <div className="card bg-white p-6 rounded-lg shadow">
          <div className="flex justify-between mb-6">
            <div className="flex gap-4">
              <select
                value={selectedStore}
                onChange={(e) => setSelectedStore(e.target.value)}
                className="p-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Stores</option>
                {stores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.name}
                  </option>
                ))}
              </select>
              <button
                className={`button px-4 py-2 rounded-lg ${
                  period === 'weekly' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'
                }`}
                onClick={() => setPeriod('weekly')}
              >
                Weekly
              </button>
              <button
                className={`button px-4 py-2 rounded-lg ${
                  period === 'monthly' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700'
                }`}
                onClick={() => setPeriod('monthly')}
              >
                Monthly
              </button>
            </div>
            <button
              className="button px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
              onClick={exportToPDF}
            >
              Export PDF
            </button>
          </div>

          <div className="dashboard-chart mb-6">
            <h2 className="card-title text-lg font-semibold text-gray-700 mb-4">Sales Trend</h2>
            <div className="chart-container h-64">
              <Line data={salesChartData} options={chartOptions} />
            </div>
          </div>

          <div className="summary-table mt-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">Summary</h3>
            <table className="table w-full border-collapse">
              <thead>
                <tr className="bg-gray-200">
                  <th className="p-3 text-left">Metric</th>
                  <th className="p-3 text-left">Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-3">Total Sales</td>
                  <td className="p-3">{formatCurrency(dashboardData.total_sales)}</td>
                </tr>
                <tr>
                  <td className="p-3">Total Spoilage</td>
                  <td className="p-3">{formatCurrency(dashboardData.total_spoilage_value)}</td>
                </tr>
                <tr>
                  <td className="p-3">Paid Suppliers</td>
                  <td className="p-3">
                    {dashboardData.paid_suppliers_count} (
                    {formatCurrency(dashboardData.paid_suppliers_amount)})
                  </td>
                </tr>
                <tr>
                  <td className="p-3">Unpaid Suppliers</td>
                  <td className="p-3">
                    {dashboardData.unpaid_suppliers_count} (
                    {formatCurrency(dashboardData.unpaid_suppliers_amount)})
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="top-products mt-6">
            <h3 className="text-lg font-semibold text-gray-700 mb-4">Top Selling Products</h3>
            <table className="table w-full border-collapse">
              <thead>
                <tr className="bg-gray-200">
                  <th className="p-3 text-left">Product</th>
                  <th className="p-3 text-left">Units Sold</th>
                  <th className="p-3 text-left">Revenue (KSh)</th>
                  <th className="p-3 text-left">Growth</th>
                </tr>
              </thead>
              <tbody>
                {topProducts.length > 0 ? (
                  topProducts.map((product, index) => (
                    <tr key={index} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                      <td className="p-3">{product.product_name}</td>
                      <td className="p-3">{product.units_sold}</td>
                      <td className="p-3">{formatCurrency(product.revenue)}</td>
                      <td className={`p-3 ${product.growth > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {product.growth > 0 ? '+' : ''}{product.growth}%
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="text-center text-gray-500 p-3">
                      No products found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StoreReports;