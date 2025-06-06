import { api } from './api';
import { ActionLog, CreateActionLogData, RejectActionLogData, ActionLogUpdate, PaginatedResponse, ActionLogComment } from '../types/actionLog';

export const actionLogService = {
  getAll: async (): Promise<PaginatedResponse<ActionLog>> => {
    const response = await api.get('/action-logs/');
    return response.data;
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

  addComment: async (id: number, data: { comment: string; parent_comment_id?: number }): Promise<ActionLogComment> => {
    const response = await api.post(`/action-logs/${id}/comments/`, data);
    return response.data;
  },

  getAssignmentHistory: async (logId: number) => {
    const response = await api.get(`/action-logs/${logId}/assignment_history/`);
    return response.data;
  }
}; 