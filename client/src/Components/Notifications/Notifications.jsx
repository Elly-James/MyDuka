import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchNotifications, markNotificationAsRead, deleteNotification } from '../../store/slices/notificationSlice';
import useSocket from '../../hooks/useSocket';
import { formatDate } from '../../utils/formatters';

const Notifications = () => {
  const dispatch = useDispatch();
  const { notifications, unreadCount, loading, error } = useSelector((state) => state.notifications);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    dispatch(fetchNotifications());
  }, [dispatch]);

  useSocket(
    (notification) => dispatch({ type: 'notifications/addNotification', payload: notification }),
    (notification) => dispatch({ type: 'notifications/updateNotification', payload: notification }),
    (id) => dispatch({ type: 'notifications/removeNotification', payload: id })
  );

  const handleMarkAsRead = (id) => {
    dispatch(markNotificationAsRead(id));
  };

  const handleDelete = (id) => {
    dispatch(deleteNotification(id));
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative bg-gray-200 text-gray-700 rounded-full w-10 h-10 flex items-center justify-center"
      >
        🔔
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs">
            {unreadCount}
          </span>
        )}
      </button>
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white shadow-lg rounded-lg max-h-96 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-lg font-semibold">Notifications</h3>
            {loading && <p>Loading...</p>}
            {error && <p className="text-red-500">{error}</p>}
            {notifications.length === 0 && !loading && <p>No notifications</p>}
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={`p-2 border-b ${notification.is_read ? 'bg-gray-100' : 'bg-white'}`}
              >
                <p>{notification.message}</p>
                <p className="text-sm text-gray-500">{formatDate(notification.created_at)}</p>
                <div className="flex gap-2 mt-1">
                  {!notification.is_read && (
                    <button
                      onClick={() => handleMarkAsRead(notification.id)}
                      className="text-blue-500 text-sm"
                    >
                      Mark as Read
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(notification.id)}
                    className="text-red-500 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Notifications;