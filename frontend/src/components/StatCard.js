import React from 'react';
import {
  UsersIcon,
  CurrencyDollarIcon,
  ClockIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

const iconMap = {
  users: UsersIcon,
  'currency-dollar': CurrencyDollarIcon,
  clock: ClockIcon,
  'chart-bar': ChartBarIcon,
};

const colorMap = {
  primary: {
    bg: 'bg-primary-50',
    text: 'text-primary-700',
    icon: 'text-primary-600',
  },
  success: {
    bg: 'bg-success-50',
    text: 'text-success-700',
    icon: 'text-success-600',
  },
  warning: {
    bg: 'bg-warning-50',
    text: 'text-warning-700',
    icon: 'text-warning-600',
  },
  secondary: {
    bg: 'bg-secondary-50',
    text: 'text-secondary-700',
    icon: 'text-secondary-600',
  },
};

const StatCard = ({ title, value, icon, color = 'primary' }) => {
  const Icon = iconMap[icon];
  const colors = colorMap[color];

  return (
    <div className={`${colors.bg} rounded-lg shadow p-6`}>
      <div className="flex items-center">
        <div className={`p-3 rounded-full ${colors.bg}`}>
          <Icon className={`h-6 w-6 ${colors.icon}`} aria-hidden="true" />
        </div>
        <div className="ml-4">
          <p className={`text-sm font-medium ${colors.text}`}>{title}</p>
          <p className={`text-2xl font-semibold ${colors.text}`}>{value}</p>
        </div>
      </div>
    </div>
  );
};

export default StatCard; 