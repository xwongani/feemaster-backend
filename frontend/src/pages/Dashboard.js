import React, { useState, useEffect } from 'react';
import { dashboardService } from '../services/dashboardService';
import StatCard from '../components/StatCard';
import RevenueChart from '../components/RevenueChart';
import RecentActivities from '../components/RecentActivities';
import PaymentMethodsChart from '../components/PaymentMethodsChart';
import GradeDistribution from '../components/GradeDistribution';
import { toast } from 'react-toastify';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [recentActivities, setRecentActivities] = useState([]);
  const [revenueData, setRevenueData] = useState(null);
  const [paymentMethodsData, setPaymentMethodsData] = useState(null);
  const [gradeDistribution, setGradeDistribution] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState('week');

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [statsRes, activitiesRes, revenueRes, paymentMethodsRes, gradeRes] = await Promise.all([
          dashboardService.getDashboardStats(),
          dashboardService.getRecentActivities(),
          dashboardService.getRevenueChartData(selectedPeriod),
          dashboardService.getPaymentMethodsChart(),
          dashboardService.getGradeDistribution()
        ]);

        setStats(statsRes.data);
        setRecentActivities(activitiesRes.data);
        setRevenueData(revenueRes.data);
        setPaymentMethodsData(paymentMethodsRes.data);
        setGradeDistribution(gradeRes.data);
      } catch (error) {
        toast.error('Failed to load dashboard data');
        console.error('Dashboard data fetch error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [selectedPeriod]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Students"
          value={stats?.total_students || 0}
          icon="users"
          color="primary"
        />
        <StatCard
          title="Total Collections"
          value={`K${stats?.total_revenue?.toFixed(2) || 0}`}
          icon="currency-dollar"
          color="success"
        />
        <StatCard
          title="Pending Payments"
          value={`K${stats?.overdue_amount?.toFixed(2) || 0}`}
          icon="clock"
          color="warning"
        />
        <StatCard
          title="Collection Rate"
          value={`${stats?.collection_rate?.toFixed(1) || 0}%`}
          icon="chart-bar"
          color="secondary"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Revenue Trend</h2>
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="rounded-md border-gray-300 text-sm focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="week">This Week</option>
              <option value="month">This Month</option>
              <option value="quarter">This Quarter</option>
              <option value="year">This Year</option>
            </select>
          </div>
          <RevenueChart data={revenueData} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Payment Methods</h2>
          <PaymentMethodsChart data={paymentMethodsData} />
        </div>
      </div>

      {/* Grade Distribution and Recent Activities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Grade Distribution</h2>
          <GradeDistribution data={gradeDistribution} />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activities</h2>
          <RecentActivities activities={recentActivities} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 