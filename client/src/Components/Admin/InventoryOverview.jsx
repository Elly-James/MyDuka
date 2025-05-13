import React, { useState, useEffect, useMemo } from 'react';
import { api, handleApiError, formatCurrency } from '../utils/api';
import useSocket from '../hooks/useSocket';
import SideBar from './SideBar';
import NavBar from '../NavBar/NavBar';
import './admin.css';

const InventoryOverview = () => {
    const [inventory, setInventory] = useState([]);
    const [filtered, setFiltered] = useState([]);
    const [categories, setCategories] = useState(['All Categories']);
    const [category, setCategory] = useState('All Categories');
    const [paymentStatus, setPaymentStatus] = useState('All');
    const [search, setSearch] = useState('');
    const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage] = useState(10);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const { socket } = useSocket();

    const handleSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                // Fetch products with expanded store and category info
                const productsResponse = await api.get('/api/inventory/products', {
                    params: {
                        per_page: 100 // Increase if you expect more than 100 products
                    }
                });

                // Fetch inventory entries for spoilage calculation
                const entriesResponse = await api.get('/api/inventory/entries', {
                    params: {
                        per_page: 500 // Adjust based on expected volume
                    }
                });

                // Process products data
                const productsData = productsResponse.data.products || [];
                const entriesData = entriesResponse.data.entries || [];

                // Calculate spoilage for each product
                const productsWithSpoilage = productsData.map(product => {
                    const productEntries = entriesData.filter(entry => entry.product_id === product.id);
                    const totalReceived = productEntries.reduce((sum, entry) => sum + entry.quantity_received, 0);
                    const totalSpoiled = productEntries.reduce((sum, entry) => sum + entry.quantity_spoiled, 0);
                    
                    // Clean payment_status by removing 'PaymentStatus.' prefix
                    const rawPaymentStatus = productEntries.length > 0 ? 
                        productEntries[0].payment_status : 'UNPAID';
                    const cleanPaymentStatus = rawPaymentStatus.replace('PaymentStatus.', '');

                    return {
                        ...product,
                        spoilage_percentage: totalReceived > 0 ? (totalSpoiled / totalReceived * 100) : 0,
                        payment_status: cleanPaymentStatus
                    };
                });

                // Extract unique categories
                const uniqueCategories = ['All Categories', ...new Set(
                    productsData
                        .map(p => p.category_name || 'Uncategorized')
                        .filter(Boolean)
                )];

                setInventory(productsWithSpoilage);
                setFiltered(productsWithSpoilage);
                setCategories(uniqueCategories);

            } catch (err) {
                handleApiError(err, setError);
                console.error('Error fetching inventory data:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    useEffect(() => {
        if (!socket) return;

        const handleStockUpdate = (data) => {
            setInventory(prev => {
                const updated = prev.map(item => 
                    item.id === data.product_id ? { 
                        ...item, 
                        current_stock: data.current_stock,
                        updated_at: data.updated_at,
                        payment_status: data.payment_status ? data.payment_status.replace('PaymentStatus.', '') : item.payment_status
                    } : item
                );
                return updated;
            });
        };

        const handleLowStock = (data) => {
            setError(`Low stock alert: ${data.message}`);
            setTimeout(() => setError(''), 5000);
        };

        socket.on('STOCK_UPDATED', handleStockUpdate);
        socket.on('LOW_STOCK', handleLowStock);

        return () => {
            socket.off('STOCK_UPDATED', handleStockUpdate);
            socket.off('LOW_STOCK', handleLowStock);
        };
    }, [socket]);

    useEffect(() => {
        let filteredList = [...inventory];
        
        // Apply filters
        if (category !== 'All Categories') {
            filteredList = filteredList.filter(item => 
                item.category_name === category
            );
        }

        if (paymentStatus !== 'All') {
            filteredList = filteredList.filter(item => 
                item.payment_status === paymentStatus
            );
        }

        if (search) {
            const searchTerm = search.toLowerCase();
            filteredList = filteredList.filter(item => 
                item.name.toLowerCase().includes(searchTerm) ||
                (item.sku && item.sku.toLowerCase().includes(searchTerm))
            );
        }

        // Apply sorting
        if (sortConfig.key) {
            filteredList.sort((a, b) => {
                const aValue = a[sortConfig.key];
                const bValue = b[sortConfig.key];
                
                // Handle null/undefined values
                if (aValue == null) return sortConfig.direction === 'asc' ? 1 : -1;
                if (bValue == null) return sortConfig.direction === 'asc' ? -1 : 1;
                
                // Numeric comparison for stock and spoilage
                if (sortConfig.key === 'current_stock' || sortConfig.key === 'spoilage_percentage') {
                    return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
                }
                
                // String comparison for names and payment status
                if (typeof aValue === 'string' && typeof bValue === 'string') {
                    return sortConfig.direction === 'asc' 
                        ? aValue.localeCompare(bValue) 
                        : bValue.localeCompare(bValue);
                }
                
                return 0;
            });
        }

        setFiltered(filteredList);
        setCurrentPage(1); // Reset to first page when filters change
    }, [search, category, paymentStatus, inventory, sortConfig]);

    const paginatedData = useMemo(() => {
        const start = (currentPage - 1) * itemsPerPage;
        return filtered.slice(start, start + itemsPerPage);
    }, [filtered, currentPage, itemsPerPage]);

    const totalPages = Math.ceil(filtered.length / itemsPerPage);

    const getStockStatusClass = (current, min) => {
        if (current <= min) return 'text-red-600 font-bold';
        if (current <= min * 1.5) return 'text-yellow-600';
        return 'text-green-600';
    };

    return (
        <div className="flex min-h-screen bg-gray-100">
            <SideBar />
            <div className="main-content flex-1 p-6 overflow-auto">
                <NavBar />

                {error && (
                    <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
                        <p>{error}</p>
                    </div>
                )}

                <div className="bg-white rounded-lg shadow p-6">
                    <h1 className="text-2xl font-bold text-gray-800 mb-6">Inventory Overview</h1>
                    
                    {/* Filters */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                            <select 
                                className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                                value={category} 
                                onChange={(e) => setCategory(e.target.value)}
                            >
                                {categories.map((cat, idx) => (
                                    <option key={idx} value={cat}>{cat}</option>
                                ))}
                            </select>
                        </div>
                        
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Status</label>
                            <select 
                                className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                                value={paymentStatus} 
                                onChange={(e) => setPaymentStatus(e.target.value)}
                            >
                                <option value="All">All</option>
                                <option value="PAID">Paid</option>
                                <option value="UNPAID">Unpaid</option>
                            </select>
                        </div>
                        
                        <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
                            <input
                                type="text"
                                className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                                placeholder="Search by product name or SKU..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                        </div>
                    </div>

                    {/* Inventory Table */}
                    <div className="overflow-x-auto">
                        {loading ? (
                            <div className="flex justify-center items-center py-12">
                                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                            </div>
                        ) : (
                            <>
                                <table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th 
                                                scope="col" 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                                onClick={() => handleSort('name')}
                                            >
                                                Product
                                                {sortConfig.key === 'name' && (
                                                    <span className="ml-1">
                                                        {sortConfig.direction === 'asc' ? '↑' : '↓'}
                                                    </span>
                                                )}
                                            </th>
                                            <th 
                                                scope="col" 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                                onClick={() => handleSort('current_stock')}
                                            >
                                                Stock
                                                {sortConfig.key === 'current_stock' && (
                                                    <span className="ml-1">
                                                        {sortConfig.direction === 'asc' ? '↑' : '↓'}
                                                    </span>
                                                )}
                                            </th>
                                            <th 
                                                scope="col" 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                                onClick={() => handleSort('spoilage_percentage')}
                                            >
                                                Spoilage Rate
                                                {sortConfig.key === 'spoilage_percentage' && (
                                                    <span className="ml-1">
                                                        {sortConfig.direction === 'asc' ? '↑' : '↓'}
                                                    </span>
                                                )}
                                            </th>
                                            <th 
                                                scope="col" 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                                onClick={() => handleSort('unit_price')}
                                            >
                                                Price
                                                {sortConfig.key === 'unit_price' && (
                                                    <span className="ml-1">
                                                        {sortConfig.direction === 'asc' ? '↑' : '↓'}
                                                    </span>
                                                )}
                                            </th>
                                            <th 
                                                scope="col" 
                                                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                                                onClick={() => handleSort('payment_status')}
                                            >
                                                Payment Status
                                                {sortConfig.key === 'payment_status' && (
                                                    <span className="ml-1">
                                                        {sortConfig.direction === 'asc' ? '↑' : '↓'}
                                                    </span>
                                                )}
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {paginatedData.length > 0 ? (
                                            paginatedData.map((item) => (
                                                <tr key={item.id} className="hover:bg-gray-50">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="flex items-center">
                                                            <div className="ml-4">
                                                                <div className="text-sm font-medium text-gray-900">
                                                                    {item.name}
                                                                </div>
                                                                <div className="text-sm text-gray-500">
                                                                    {item.sku || 'No SKU'}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm">
                                                            <span className={getStockStatusClass(item.current_stock, item.min_stock_level)}>
                                                                {item.current_stock}
                                                            </span>
                                                            <span className="text-xs text-gray-500 ml-1">
                                                                /{item.min_stock_level} min
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="text-sm">
                                                            {item.spoilage_percentage.toFixed(2)}%
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {formatCurrency(item.unit_price)}
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                                                            ${item.payment_status === 'PAID' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                                            {item.payment_status || 'UNPAID'}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan="5" className="px-6 py-4 text-center text-sm text-gray-500">
                                                    {filtered.length === 0 && !loading ? 'No inventory items match your filters' : 'Loading...'}
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>

                                {/* Pagination */}
                                {totalPages > 1 && (
                                    <div className="flex items-center justify-between mt-4 px-4 py-3 bg-white border-t border-gray-200 sm:px-6">
                                        <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                                            <div>
                                                <p className="text-sm text-gray-700">
                                                    Showing <span className="font-medium">{(currentPage - 1) * itemsPerPage + 1}</span> to{' '}
                                                    <span className="font-medium">{Math.min(currentPage * itemsPerPage, filtered.length)}</span> of{' '}
                                                    <span className="font-medium">{filtered.length}</span> results
                                                </p>
                                            </div>
                                            <div>
                                                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                                                    <button
                                                        onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                                                        disabled={currentPage === 1}
                                                        className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                                    >
                                                        <span className="sr-only">Previous</span>
                                                        ←
                                                    </button>
                                                    
                                                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                                        let pageNum;
                                                        if (totalPages <= 5) {
                                                            pageNum = i + 1;
                                                        } else if (currentPage <= 3) {
                                                            pageNum = i + 1;
                                                        } else if (currentPage >= totalPages - 2) {
                                                            pageNum = totalPages - 4 + i;
                                                        } else {
                                                            pageNum = currentPage - 2 + i;
                                                        }
                                                        
                                                        return (
                                                            <button
                                                                key={pageNum}
                                                                onClick={() => setCurrentPage(pageNum)}
                                                                className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium 
                                                                    ${currentPage === pageNum 
                                                                        ? 'z-10 bg-blue-50 border-blue-500 text-blue-600' 
                                                                        : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'}`}
                                                            >
                                                                {pageNum}
                                                            </button>
                                                        );
                                                    })}
                                                    
                                                    <button
                                                        onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                                                        disabled={currentPage === totalPages}
                                                        className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                                    >
                                                        <span className="sr-only">Next</span>
                                                        →
                                                    </button>
                                                </nav>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default InventoryOverview;