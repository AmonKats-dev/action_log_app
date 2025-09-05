import { api } from './api';
import { ActionLog, CreateActionLogData, RejectActionLogData, ActionLogUpdate, PaginatedResponse, ActionLogComment } from '../types/actionLog';

export const actionLogService = {
  getAll: async (): Promise<ActionLog[]> => {
    try {
      const response = await api.get('/action-logs/');
      console.log('Raw API response:', response);
      // If the response is a paginated response, return the results
      if (response.data && 'results' in response.data) {
        return response.data.results;
      }
      // If the response is an array, return it directly
      if (Array.isArray(response.data)) {
        return response.data;
      }
      // If the response is a single object, return it as an array
      if (typeof response.data === 'object') {
        return [response.data];
      }
      // If none of the above, return empty array
      return [];
    } catch (error) {
      console.error('Error in actionLogService.getAll:', error);
      return [];
    }
  },

  getById: async (id: number): Promise<ActionLog> => {
    const response = await api.get(`/action-logs/${id}/`);
    return response.data;
  },

  create: async (data: CreateActionLogData): Promise<ActionLog> => {
    const response = await api.post('/action-logs/', data);
    return response.data;
  },

  update: async (id: number, data: ActionLogUpdate): Promise<ActionLog> => {
    const response = await api.patch(`/action-logs/${id}/`, data);
    return response.data;
  },

  approve: async (id: number): Promise<ActionLog> => {
    const response = await api.post(`/action-logs/${id}/approve/`);
    return response.data;
  },

  reject: async (id: number, data: RejectActionLogData): Promise<ActionLog> => {
    const response = await api.post(`/action-logs/${id}/reject/`, data);
    return response.data;
  },

  assign: async (id: number, userId: number): Promise<ActionLog> => {
    const response = await api.post(`/action-logs/${id}/assign/`, { assigned_to: userId });
    return response.data;
  },

  getComments: async (id: number): Promise<ActionLogComment[]> => {
    const response = await api.get(`/action-logs/${id}/comments/`);
    return response.data;
  },

  addComment: async (id: number, data: { comment: string; parent_id?: number }): Promise<ActionLogComment> => {
    const response = await api.post(`/action-logs/${id}/comments/`, data);
    return response.data;
  },

  getAssignmentHistory: async (logId: number) => {
    const response = await api.get(`/action-logs/${logId}/assignment_history/`);
    return response.data;
  },

  getUnreadNotificationCount: async (logId: number) => {
    const response = await api.get(`/action-logs/${logId}/unread_notifications/`);
    return response.data.unread_count;
  },

  markNotificationsRead: async (logId: number) => {
    const response = await api.post(`/action-logs/${logId}/mark_notifications_read/`);
    return response.data.marked_read;
  }
}; 