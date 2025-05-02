import { useEffect, useState, useRef } from "react";
import api from "../utils/api";
import {
    Chart as ChartJS,
    LineElement,
    BarElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Tooltip,
    Legend,
} from "chart.js";
import { Line, Bar } from "react-chartjs-2";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import "./admin.css";

// Register Chart.js components
ChartJS.register(LineElement, BarElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend);

const Reports = () => {
    const [tab, setTab] = useState("weekly");
    const [salesTrend, setSalesTrend] = useState([]);
    const [labels, setLabels] = useState([]);
    const [topProducts, setTopProducts] = useState([]);

    const exportRef = useRef(null);

    useEffect(() => {
        const fetchReports = async () => {
            try {
                const res = await api.get(`/api/reports/sales?period=${tab}`);
                const data = res.data;

                setLabels(data.chart_data.labels || []);
                setSalesTrend(data.chart_data.values || []);
                setTopProducts(data.top_products || []);
            } catch (err) {
                console.error(`Failed to load ${tab} report:`, err);
            }
        };

        fetchReports();
    }, [tab]);

    const handleExportPDF = () => {
        const input = exportRef.current;
        if (!input) return;

        html2canvas(input, { scale: 2 }).then((canvas) => {
            const imgData = canvas.toDataURL("image/png");
            const pdf = new jsPDF("p", "mm", "a4");
            const width = pdf.internal.pageSize.getWidth();
            const height = (canvas.height * width) / canvas.width;

            pdf.addImage(imgData, "PNG", 0, 0, width, height);
            pdf.save(`MyDuka_Report_${tab}.pdf`);
        });
    };

    const salesLineChart = {
        labels,
        datasets: [
            {
                label: "Sales",
                data: salesTrend,
                borderColor: "#3b82f6",
                tension: 0.3,
                fill: false,
            },
        ],
    };

    const barChart = {
        labels: topProducts.map((p) => p.name),
        datasets: [
            {
                label: "sales",
                data: topProducts.map((p) => p.sales),
                backgroundColor: "#3730a3",
            },
            {
                label: "profit",
                data: topProducts.map((p) => p.profit),
                backgroundColor: "#10b981",
            },
        ],
    };

    return (
        <div className="inventory-container">
            <h2 className="inventory-title">Reports</h2>

            {/* Tabs & Export */}
            <div className="flex-space-between" style={{ marginBottom: "1.5rem" }}>
                <div>
                    {["weekly", "monthly", "annual"].map((t) => (
                        <button
                            key={t}
                            className={`tab-button ${tab === t ? "active-tab" : ""}`}
                            onClick={() => setTab(t)}
                        >
                            {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                    ))}
                </div>
                <button className="add-button" onClick={handleExportPDF}>
                    Export PDF
                </button>
            </div>

            {/* Charts to export */}
            <div ref={exportRef}>
                {/* Line Chart */}
                <div className="chart-card">
                    <h4>Sales Trend ({tab.charAt(0).toUpperCase() + tab.slice(1)})</h4>
                    <Line data={salesLineChart} />
                </div>

                {/* Bar Chart */}
                <div className="chart-card">
                    <h4>Top Products by Sales</h4>
                    <Bar data={barChart} />
                </div>
            </div>
        </div>
    );
};

export default Reports;