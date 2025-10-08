/**
 * GOV.UK Notification Component
 * Simple notification system using GOV.UK notification banner
 */

import React, { useState, useEffect } from 'react';

export interface NotificationProps {
  title: string;
  message: string;
  type?: 'success' | 'warning' | 'error' | 'info';
  autoHide?: boolean;
  onClose?: () => void;
}

interface NotificationState extends NotificationProps {
  id: string;
  visible: boolean;
}

// Simple notification store
class NotificationStore {
  private notifications: NotificationState[] = [];
  private listeners: Array<(notifications: NotificationState[]) => void> = [];

  show(notification: NotificationProps) {
    const id = Math.random().toString(36).substr(2, 9);
    const newNotification: NotificationState = {
      ...notification,
      id,
      visible: true
    };

    this.notifications.push(newNotification);
    this.notify();

    if (notification.autoHide !== false) {
      setTimeout(() => {
        this.hide(id);
      }, 5000);
    }

    return id;
  }

  hide(id: string) {
    this.notifications = this.notifications.filter(n => n.id !== id);
    this.notify();
  }

  subscribe(listener: (notifications: NotificationState[]) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notify() {
    this.listeners.forEach(listener => listener([...this.notifications]));
  }
}

export const notificationStore = new NotificationStore();

// Hook for using notifications
export const useNotifications = () => {
  const [notifications, setNotifications] = useState<NotificationState[]>([]);

  useEffect(() => {
    return notificationStore.subscribe(setNotifications);
  }, []);

  return {
    notifications,
    show: (notification: NotificationProps) => notificationStore.show(notification),
    hide: (id: string) => notificationStore.hide(id)
  };
};

// Notification component
const Notification: React.FC<NotificationState> = ({ 
  id, 
  title, 
  message, 
  type = 'info', 
  onClose 
}) => {
  const getTypeClass = () => {
    switch (type) {
      case 'success':
        return 'govuk-notification-banner--success';
      case 'warning':
      case 'error':
        return '';
      default:
        return '';
    }
  };

  const getTypeRole = () => {
    switch (type) {
      case 'success':
        return 'alert';
      case 'error':
      case 'warning':
        return 'alert';
      default:
        return 'region';
    }
  };

  const handleClose = () => {
    if (onClose) onClose();
    notificationStore.hide(id);
  };

  return (
    <div 
      className={`govuk-notification-banner ${getTypeClass()}`}
      role={getTypeRole()}
      aria-labelledby={`notification-title-${id}`}
      data-module="govuk-notification-banner"
    >
      <div className="govuk-notification-banner__header">
        <h2 className="govuk-notification-banner__title" id={`notification-title-${id}`}>
          {type === 'success' ? 'Success' : 
           type === 'error' ? 'Error' :
           type === 'warning' ? 'Warning' : 'Information'}
        </h2>
      </div>
      <div className="govuk-notification-banner__content">
        <h3 className="govuk-notification-banner__heading">
          {title}
        </h3>
        <p className="govuk-body">{message}</p>
        <button 
          className="govuk-button govuk-button--secondary govuk-!-margin-top-2"
          onClick={handleClose}
        >
          Dismiss
        </button>
      </div>
    </div>
  );
};

// Container component for notifications
export const NotificationContainer: React.FC = () => {
  const { notifications } = useNotifications();

  if (notifications.length === 0) {
    return null;
  }

  return (
    <div style={{ position: 'fixed', top: '20px', right: '20px', zIndex: 1000, maxWidth: '400px' }}>
      {notifications.map(notification => (
        <div key={notification.id} style={{ marginBottom: '10px' }}>
          <Notification {...notification} />
        </div>
      ))}
    </div>
  );
};

export default Notification;
