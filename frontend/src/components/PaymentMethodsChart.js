import React from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Doughnut } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend);

const PaymentMethodsChart = ({ data }) => {
  if (!data) return null;

  const chartData = {
    labels: data.labels || [],
    datasets: [
      {
        data: data.datasets?.[0]?.data || [],
        backgroundColor: [
          'rgb(14, 165, 233)', // primary-500
          'rgb(34, 197, 94)',  // success-500
          'rgb(245, 158, 11)', // warning-500
          'rgb(99, 102, 241)', // indigo-500
        ],
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'bottom',
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.raw || 0;
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = ((value / total) * 100).toFixed(1);
            return `${label}: K${value.toFixed(2)} (${percentage}%)`;
          }
        }
      }
    },
  };

  return (
    <div className="h-80">
      <Doughnut data={chartData} options={options} />
    </div>
  );
};

export default PaymentMethodsChart; 