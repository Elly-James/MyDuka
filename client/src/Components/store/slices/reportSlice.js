import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '../../utils/api';

export const fetchSalesReport = createAsyncThunk(
  'reports/fetchSalesReport',
  async ({ period, store_id }, { rejectWithValue }) => {
    try {
      if (!['weekly', 'monthly'].includes(period)) {
        throw new Error('Invalid period. Use weekly or monthly');
      }
      const response = await api.get(`/api/reports/sales?period=${period}${store_id ? `&store_id=${store_id}` : ''}`);
      if (response.data.message === 'No accessible stores for this user') {
        return { chart_data: { labels: [], datasets: [] }, total_quantity_sold: 0, total_revenue: 0 };
      }
      return response.data.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || err.message || 'Failed to fetch sales report');
    }
  }
);

export const fetchSpoilageReport = createAsyncThunk(
  'reports/fetchSpoilageReport',
  async ({ period, store_id }, { rejectWithValue }) => {
    try {
      if (!['weekly', 'monthly'].includes(period)) {
        throw new Error('Invalid period. Use weekly or monthly');
      }
      const response = await api.get(`/api/reports/spoilage?period=${period}${store_id ? `&store_id=${store_id}` : ''}`);
      if (response.data.message === 'No accessible stores for this user') {
        return { chart_data: { labels: [], datasets: [] }, total_spoilage_value: 0 };
      }
      return response.data.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || err.message || 'Failed to fetch spoilage report');
    }
  }
);

export const fetchTopProducts = createAsyncThunk(
  'reports/fetchTopProducts',
  async ({ period, store_id }, { rejectWithValue }) => {
    try {
      if (!['weekly', 'monthly'].includes(period)) {
        throw new Error('Invalid period. Use weekly or monthly');
      }
      const response = await api.get(`/api/reports/top-products?period=${period}${store_id ? `&store_id=${store_id}` : ''}`);
      if (response.data.message === 'No accessible stores for this user') {
        return [];
      }
      return response.data.top_products;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || err.message || 'Failed to fetch top products');
    }
  }
);

export const fetchDashboardSummary = createAsyncThunk(
  'reports/fetchDashboardSummary',
  async ({ period, store_id }, { rejectWithValue }) => {
    try {
      if (!['weekly', 'monthly'].includes(period)) {
        throw new Error('Invalid period. Use weekly or monthly');
      }
      const response = await api.get(`/api/reports/dashboard/summary?period=${period}${store_id ? `&store_id=${store_id}` : ''}`);
      if (response.data.message === 'No accessible stores for this user') {
        return {
          low_stock_count: 0,
          low_stock_products: [],
          normal_stock_count: 0,
          total_sales: 0,
          total_spoilage_value: 0,
          spoilage_percentage: 0,
          unpaid_suppliers_count: 0,
          unpaid_suppliers_amount: 0,
          paid_suppliers_count: 0,
          paid_suppliers_amount: 0,
          paid_percentage: 0,
          unpaid_percentage: 0,
        };
      }
      return response.data.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || err.message || 'Failed to fetch dashboard summary');
    }
  }
);

const reportSlice = createSlice({
  name: 'reports',
  initialState: {
    salesReport: null,
    spoilageReport: null,
    topProducts: [],
    dashboardSummary: null,
    loading: false,
    error: null,
  },
  reducers: {
    clearReports: (state) => {
      state.salesReport = null;
      state.spoilageReport = null;
      state.topProducts = [];
      state.dashboardSummary = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSalesReport.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSalesReport.fulfilled, (state, action) => {
        state.salesReport = action.payload;
        state.loading = false;
      })
      .addCase(fetchSalesReport.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchSpoilageReport.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSpoilageReport.fulfilled, (state, action) => {
        state.spoilageReport = action.payload;
        state.loading = false;
      })
      .addCase(fetchSpoilageReport.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchTopProducts.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTopProducts.fulfilled, (state, action) => {
        state.topProducts = action.payload;
        state.loading = false;
      })
      .addCase(fetchTopProducts.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchDashboardSummary.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardSummary.fulfilled, (state, action) => {
        state.dashboardSummary = action.payload;
        state.loading = false;
      })
      .addCase(fetchDashboardSummary.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { clearReports } = reportSlice.actions;
export default reportSlice.reducer;