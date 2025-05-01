import React, { useState, useEffect } from 'react';
import api from '../../utils/api';

const ActivityLog = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await api.get('/api/activity-logs'); // Assuming this endpoint exists
        setLogs(response.data);
      } catch (err) {
        setError('Failed to fetch activity logs');
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  if (loading) return <div className="text-center text-gray-500">Loading...</div>;
  if (error) return <div className="text-center text-red-500">{error}</div>;

  return (
    <div className="bg-white p-4 rounded shadow border border-gray-200 mt-4 overflow-x-auto">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">Activity Log</h3>
      <table className="w-full text-left table-auto">
        <thead>
          <tr className="bg-gray-100 border-b">
            <th className="p-2 text-gray-700">Time</th>
            <th className="p-2 text-gray-700">Action</th>
            <th className="p-2 text-gray-700">Status</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} className="border-b hover:bg-gray-50">
              <td className="p-2 text-gray-600">{log.time}</td>
              <td className="p-2 text-gray-600">{log.action}</td>
              <td className="p-2">
                <span
                  className={`inline-block px-2 py-1 rounded text-white ${
                    log.status === 'Success' ? 'bg-green-500' : log.status === 'Pending' ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                >
                  {log.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ActivityLog;

