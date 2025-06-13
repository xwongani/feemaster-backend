import React from 'react';
import { format } from 'date-fns';

const statusColors = {
  completed: 'bg-success-100 text-success-800',
  pending: 'bg-warning-100 text-warning-800',
  failed: 'bg-danger-100 text-danger-800',
};

const RecentActivities = ({ activities }) => {
  if (!activities || activities.length === 0) {
    return (
      <div className="text-center text-gray-500 py-4">
        No recent activities
      </div>
    );
  }

  return (
    <div className="flow-root">
      <ul role="list" className="-mb-8">
        {activities.map((activity, activityIdx) => (
          <li key={activity.id}>
            <div className="relative pb-8">
              {activityIdx !== activities.length - 1 ? (
                <span
                  className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200"
                  aria-hidden="true"
                />
              ) : null}
              <div className="relative flex space-x-3">
                <div>
                  <span className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center ring-8 ring-white">
                    <span className="text-sm font-medium text-primary-600">
                      {activity.initials}
                    </span>
                  </span>
                </div>
                <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                  <div>
                    <p className="text-sm text-gray-500">
                      Payment of{' '}
                      <span className="font-medium text-gray-900">
                        K{activity.amount.toFixed(2)}
                      </span>{' '}
                      by{' '}
                      <span className="font-medium text-gray-900">
                        {activity.student_name}
                      </span>
                    </p>
                  </div>
                  <div className="text-right text-sm whitespace-nowrap text-gray-500">
                    <time dateTime={activity.datetime}>
                      {format(new Date(activity.datetime), 'MMM d, h:mm a')}
                    </time>
                    <span
                      className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        statusColors[activity.status]
                      }`}
                    >
                      {activity.status}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default RecentActivities; 