import { useEffect, useState } from "react";
import api from "../utils/api";
import { Line } from "react-chartjs-2";
import InventoryOverview from "./InventoryOverview";
import "./admin.css";

// Chart.js setup
import {
    Chart as ChartJS,
    LineElement,
    PointElement,
    LinearScale,
    CategoryScale,
    Tooltip,
    Legend,
} from "chart.js";

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend);

const Dashboard = () => {
    const [activeTab, setActiveTab] = useState("clerks");
    const [clerks, setClerks] = useState([]);
    const [showModal, setShowModal] = useState(false);
    const [formData, setFormData] = useState({ name: "", email: "", password: "" });

    // Fetch Clerks on Mount
    useEffect(() => {
        const fetchClerks = async () => {
            try {
                const response = await api.get("/api/users?role=CLERK");
                setClerks(response.data);
            } catch (error) {
                console.error("Failed to fetch clerks:", error);
            }
        };

        fetchClerks();
    }, []);

    const handleDeactivate = async (id) => {
        try {
            await api.put(`/api/users/${id}/status`, { status: "inactive" });
            setClerks((prev) =>
                prev.map((c) => (c.id === id ? { ...c, status: "inactive" } : c))
            );
        } catch (error) {
            console.error("Deactivate failed:", error);
        }
    };

    const handleDelete = async (id) => {
        try {
            await api.delete(`/api/users/${id}`);
            setClerks((prev) => prev.filter((c) => c.id !== id));
        } catch (error) {
            console.error("Delete failed:", error);
        }
    };

    const handleAddClerk = async () => {
        try {
            const payload = {
                email: formData.email,
                password: formData.password,
                name: formData.name,
                token: "CLERK_INVITE_TOKEN", // Replace with actual invite token
            };
            const response = await api.post("/api/auth/register", payload);
            setClerks((prev) => [...prev, response.data]);
            setShowModal(false);
            setFormData({ name: "", email: "", password: "" });
        } catch (error) {
            console.error("Add Clerk failed:", error);
            alert("Failed to add clerk.");
        }
    };

    const chartData = {
        labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
        datasets: [
            {
                label: "Clerk Activity",
                data: [35, 45, 70, 60, 80, 90, 65, 75],
                fill: false,
                borderColor: "#3b82f6",
                tension: 0.3,
            },
        ],
    };

    return (
        <div className="inventory-container">
            <h2 className="inventory-title">Admin Dashboard</h2>

            {/* Tabs */}
            <div style={{ marginBottom: "1.5rem" }}>
                {["clerks", "inventory", "requests"].map((tab) => (
                    <button
                        key={tab}
                        className={`tab-button ${activeTab === tab ? "active-tab" : ""}`}
                        onClick={() => setActiveTab(tab)}
                    >
                        {tab === "clerks"
                            ? "Clerk Management"
                            : tab === "inventory"
                                ? "Inventory Overview"
                                : "Supply Requests"}
                    </button>
                ))}
            </div>

            {/* Clerk Management Tab */}
            {activeTab === "clerks" && (
                <>
                    <div className="flex-space-between" style={{ marginBottom: "1rem" }}>
                        <span style={{ fontWeight: "500" }}>Clerk List</span>
                        <button className="add-button" onClick={() => setShowModal(true)}>
                            + Add Clerk
                        </button>
                    </div>

                    <table className="inventory-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Last Active</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {clerks.map((clerk) => (
                                <tr key={clerk.id}>
                                    <td>{clerk.name}</td>
                                    <td>{clerk.email}</td>
                                    <td>{clerk.last_active || "—"}</td>
                                    <td>
                                        <button
                                            onClick={() => handleDeactivate(clerk.id)}
                                            className="small-button"
                                        >
                                            Deactivate
                                        </button>
                                        <button
                                            onClick={() => handleDelete(clerk.id)}
                                            className="small-button danger"
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>

                    {/* Clerk Performance Chart */}
                    <div style={{ marginTop: "2rem" }}>
                        <h3 style={{ marginBottom: "1rem" }}>Clerk Performance</h3>
                        <Line data={chartData} />
                    </div>
                </>
            )}

            {/* Inventory Tab */}
            {activeTab === "inventory" && <InventoryOverview />}

            {/* Requests Tab */}
            {activeTab === "requests" && <p>Supply Requests view coming soon...</p>}

            {/* Add Clerk Modal */}
            {showModal && (
                <div className="modal-backdrop">
                    <div className="modal">
                        <h3>Add Clerk</h3>
                        <input
                            type="text"
                            placeholder="Name"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        />
                        <input
                            type="email"
                            placeholder="Email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        />
                        <input
                            type="password"
                            placeholder="Password"
                            value={formData.password}
                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        />

                        <div className="modal-actions">
                            <button className="small-button" onClick={() => setShowModal(false)}>
                                Cancel
                            </button>
                            <button className="small-button" onClick={handleAddClerk}>
                                Add
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
