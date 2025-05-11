import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '../../utils/api';

export const fetchNotifications = createAsyncThunk(
  'notifications/fetchNotifications',
  async ({ page = 1, perPage = 10, isRead = null }, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({ page, per_page: perPage });
      if (isRead !== null) params.append('is_read', isRead);
      const response = await api.get(`/api/notifications?${params.toString()}`);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || 'Failed to fetch notifications');
    }
  }
);

export const markNotificationAsRead = createAsyncThunk(
  'notifications/markAsRead',
  async (id, { rejectWithValue }) => {
    try {
      await api.put(`/api/notifications/${id}/read`);
      return id;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || 'Failed to mark notification as read');
    }
  }
);

export const deleteNotification = createAsyncThunk(
  'notifications/deleteNotification',
  async (id, { rejectWithValue }) => {
    try {
      await api.delete(`/api/notifications/${id}`);
      return id;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || 'Failed to delete notification');
    }
  }
);

export const markAllNotificationsAsRead = createAsyncThunk(
  'notifications/markAllAsRead',
  async (_, { rejectWithValue }) => {
    try {
      await api.put('/api/notifications/mark-all-read');
      return true;
    } catch (err) {
      return rejectWithValue(err.response?.data?.message || 'Failed to mark all notifications as read');
    }
  }
);

const notificationSlice = createSlice({
  name: 'notifications',
  initialState: {
    notifications: [],
    unreadCount: 0,
    total: 0,
    pages: 1,
    currentPage: 1,
    loading: false,
    error: null,
  },
  reducers: {
    addNotification: (state, action) => {
      if (!import.meta.env.PROD) {
        console.log('Adding notification:', action.payload);
      }
      state.notifications.unshift(action.payload);
      if (!action.payload.is_read) state.unreadCount += 1;
      state.total += 1;
    },
    updateNotification: (state, action) => {
      const index = state.notifications.findIndex((n) => n.id === action.payload.id);
      if (index !== -1) {
        const wasUnread = !state.notifications[index].is_read;
        state.notifications[index] = action.payload;
        if (wasUnread && action.payload.is_read) state.unreadCount -= 1;
      }
    },
    removeNotification: (state, action) => {
      const index = state.notifications.findIndex((n) => n.id === action.payload);
      if (index !== -1) {
        const wasUnread = !state.notifications[index].is_read;
        state.notifications.splice(index, 1);
        if (wasUnread) state.unreadCount -= 1;
        state.total -= 1;
      }
    },
    updateBulkNotifications: (state, action) => {
      const { updated_count } = action.payload;
      state.notifications.forEach((n) => {
        if (!n.is_read) {
          n.is_read = true;
          n.updated_at = action.payload.updated_at;
        }
      });
      state.unreadCount = 0;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchNotifications.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchNotifications.fulfilled, (state, action) => {
        state.notifications = action.payload.notifications;
        state.total = action.payload.total;
        state.pages = action.payload.pages;
        state.currentPage = action.payload.page;
        state.unreadCount = action.payload.notifications.filter((n) => !n.is_read).length;
        state.loading = false;
      })
      .addCase(fetchNotifications.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(markNotificationAsRead.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(markNotificationAsRead.fulfilled, (state, action) => {
        const index = state.notifications.findIndex((n) => n.id === action.payload);
        if (index !== -1) {
          state.notifications[index].is_read = true;
          state.unreadCount = state.notifications.filter((n) => !n.is_read).length;
        }
        state.loading = false;
      })
      .addCase(markNotificationAsRead.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(deleteNotification.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteNotification.fulfilled, (state, action) => {
        state.notifications = state.notifications.filter((n) => n.id !== action.payload);
        state.unreadCount = state.notifications.filter((n) => !n.is_read).length;
        state.total -= 1;
        state.loading = false;
      })
      .addCase(deleteNotification.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(markAllNotificationsAsRead.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(markAllNotificationsAsRead.fulfilled, (state) => {
        state.notifications.forEach((n) => (n.is_read = true));
        state.unreadCount = 0;
        state.loading = false;
      })
      .addCase(markAllNotificationsAsRead.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { addNotification, updateNotification, removeNotification, updateBulkNotifications } = notificationSlice.actions;
export default notificationSlice.reducer;