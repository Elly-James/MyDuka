// src/Components/Admin/Reports.jsx
import React, { useState, useEffect, useRef } from 'react';
import { api, handleApiError } from '../utils/api';
import { Bar, Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import './admin.css';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    LineElement,
    PointElement,
    Title,
    Tooltip,
    Legend
);

const Reports = () => {
    const [period, setPeriod] = useState('weekly');
    const [salesData, setSalesData] = useState({ labels: [], datasets: [] });
    const [topProducts, setTopProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const pdfRef = useRef();

    useEffect(() => {
        const fetchReports = async () => {
            try {
                setLoading(true);
                const response = await api.get(`/api/reports?period=${period}`);
                const data = response.data;

                setSalesData({
                    labels: data.sales.labels,
                    datasets: [{
                        label: 'Sales',
                        data: data.sales.values,
                        borderColor: '#4f46e5',
                        backgroundColor: '#4f46e5',
                        tension: 0.1
                    }]
                });

                setTopProducts(data.top_products);

            } catch (err) {
                handleApiError(err, setError);
            } finally {
                setLoading(false);
            }
        };

        fetchReports();
    }, [period]);

    const handleExportPDF = async () => {
        const element = pdfRef.current;
        const canvas = await html2canvas(element);
        const data = canvas.toDataURL('image/png');

        const pdf = new jsPDF();
        const imgProperties = pdf.getImageProperties(data);
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (imgProperties.height * pdfWidth) / imgProperties.width;

        pdf.addImage(data, 'PNG', 0, 0, pdfWidth, pdfHeight);
        pdf.save(`myduka-report-${period}.pdf`);
    };

    const productChartData = {
        labels: topProducts.map(p => p.name),
        datasets: [{
            label: 'Revenue',
            data: topProducts.map(p => p.revenue),
            backgroundColor: '#10b981'
        }]
    };

    return (
        <div className="admin-container">
            <SideBar />
            <div className="main-content">
                <NavBar />

                {error && <div className="alert error">{error}</div>}
                {loading && <div className="loading">Loading reports...</div>}

                <div className="header">
                    <h1>Reports</h1>
                    <div className="period-selector">
                        <button
                            className={`tab ${period === 'weekly' ? 'active' : ''}`}
                            onClick={() => setPeriod('weekly')}
                        >
                            Weekly
                        </button>
                        <button
                            className={`tab ${period === 'monthly' ? 'active' : ''}`}
                            onClick={() => setPeriod('monthly')}
                        >
                            Monthly
                        </button>
                        <button
                            className={`tab ${period === 'annual' ? 'active' : ''}`}
                            onClick={() => setPeriod('annual')}
                        >
                            Annual
                        </button>
                        <button onClick={handleExportPDF} className="btn-primary">
                            Export PDF
                        </button>
                    </div>
                </div>

                <div ref={pdfRef} className="report-content">
                    <div className="card">
                        <h2>Sales Trend ({period})</h2>
                        <div className="chart-container">
                            <Line data={salesData} />
                        </div>
                    </div>

                    <div className="card">
                        <h2>Top Products</h2>
                        <div className="chart-container">
                            <Bar data={productChartData} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Reports;