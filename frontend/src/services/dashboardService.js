import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const dashboardService = {
  async getDashboardStats() {
    try {
      const response = await axios.get(`${API_URL}/dashboard/stats`);
      return response.data;
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      throw error;
    }
  },

  async getRecentActivities(limit = 10) {
    try {
      const response = await axios.get(`${API_URL}/dashboard/recent-activities`, {
        params: { limit }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching recent activities:', error);
      throw error;
    }
  },

  async getFinancialSummary(dateFrom, dateTo) {
    try {
      const response = await axios.get(`${API_URL}/dashboard/financial-summary`, {
        params: { date_from: dateFrom, date_to: dateTo }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching financial summary:', error);
      throw error;
    }
  },

  async getRevenueChartData(period = 'week') {
    try {
      const response = await axios.get(`${API_URL}/dashboard/revenue-chart`, {
        params: { period }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching revenue chart data:', error);
      throw error;
    }
  },

  async getPaymentMethodsChart(dateFrom, dateTo) {
    try {
      const response = await axios.get(`${API_URL}/dashboard/payment-methods-chart`, {
        params: { date_from: dateFrom, date_to: dateTo }
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching payment methods chart:', error);
      throw error;
    }
  },

  async getGradeDistribution() {
    try {
      const response = await axios.get(`${API_URL}/dashboard/grade-distribution`);
      return response.data;
    } catch (error) {
      console.error('Error fetching grade distribution:', error);
      throw error;
    }
  }
}; 