import api from './api';

export interface Recipient {
  id: string;
  name: string;
  phone: string;
}

export interface MessageHistory {
  sid: string;
  to: string;
  from: string;
  body: string;
  status: string;
  date_sent: string;
  direction: string;
}

export interface RecipientGroup {
  group_type: string;
  recipients: Recipient[];
}

export const messagingService = {
  async sendMessage(message: string, recipients: Recipient[], groupType?: string) {
    const response = await api.post('/messaging/send', {
      message,
      recipients,
      group_type: groupType
    });
    return response.data;
  },

  async getMessageHistory(limit: number = 100) {
    const response = await api.get(`/messaging/history?limit=${limit}`);
    return response.data;
  },

  async getRecipientGroups() {
    const response = await api.get('/messaging/recipient-groups');
    return response.data;
  }
}; 