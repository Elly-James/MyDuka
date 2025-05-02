import { useState, useEffect } from "react";
import api from "../utils/api"; // Adjust path if needed
import "./admin.css";

const InventoryOverview = () => {
    const [products, setProducts] = useState([]);
    const [filtered, setFiltered] = useState([]);
    const [categories, setCategories] = useState([]);
    const [category, setCategory] = useState("All");
    const [status, setStatus] = useState("All");
    const [search, setSearch] = useState("");

    useEffect(() => {
        const fetchInventory = async () => {
            try {
                const response = await api.get("/api/inventory/entries");
                const data = response.data;

                setProducts(data);
                setFiltered(data);

                const categorySet = new Set(data.map(item => item.category || "Uncategorized"));
                setCategories(["All", ...Array.from(categorySet)]);
            } catch (error) {
                console.error("Failed to fetch inventory:", error);
            }
        };

        fetchInventory();
    }, []);

    useEffect(() => {
        const filteredList = products.filter(item => {
            const matchSearch = item.product_name.toLowerCase().includes(search.toLowerCase());
            const matchStatus = status === "All" || item.payment_status === status;
            const matchCategory = category === "All" || item.category === category;
            return matchSearch && matchStatus && matchCategory;
        });

        setFiltered(filteredList);
    }, [search, status, category, products]);

    return (
        <div className="inventory-container">
            <h2 className="inventory-title">Inventory Overview</h2>

            <div className="inventory-filters">
                <select value={category} onChange={(e) => setCategory(e.target.value)}>
                    {categories.map((cat, idx) => (
                        <option key={idx} value={cat}>
                            {cat}
                        </option>
                    ))}
                </select>

                <select value={status} onChange={(e) => setStatus(e.target.value)}>
                    <option value="All">All</option>
                    <option value="Paid">Paid</option>
                    <option value="Unpaid">Unpaid</option>
                </select>

                <input
                    type="text"
                    placeholder="Search products..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            <table className="inventory-table">
                <thead>
                    <tr>
                        <th>Product Name</th>
                        <th>Stock Left</th>
                        <th>Spoilage Rate</th>
                        <th>Price (KSh)</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {filtered.map((item, idx) => (
                        <tr key={idx}>
                            <td>{item.product_name}</td>
                            <td className={item.quantity_left <= 10 ? "low-stock" : ""}>
                                {item.quantity_left}
                            </td>
                            <td>{item.spoilage_rate || "0%"}</td>
                            <td>{item.unit_price?.toFixed(2) || "0.00"}</td>
                            <td>
                                <span
                                    className={`status-badge ${item.payment_status === "Paid" ? "status-paid" : "status-unpaid"
                                        }`}
                                >
                                    {item.payment_status}
                                </span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <div className="inventory-pagination">
                {[1, 2, 3, 4].map(pg => (
                    <button key={pg}>{pg}</button>
                ))}
            </div>
        </div>
    );
};

export default InventoryOverview;
