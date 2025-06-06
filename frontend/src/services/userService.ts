import { api } from './api';
import { User } from '../types/user';

export const userService = {
  getAll: async (): Promise<User[]> => {
    try {
      console.log('Fetching all users...');
      const response = await api.get('/users/');
      console.log('Users API response:', response);
      
      // Handle different response structures
      let users: User[] = [];
      if (response.data) {
        if (Array.isArray(response.data)) {
          users = response.data as User[];
        } else if (response.data.results && Array.isArray(response.data.results)) {
          users = response.data.results as User[];
        } else if (typeof response.data === 'object') {
          // If it's a single user object, wrap it in an array
          users = [response.data as User];
        }
      }
      
      console.log('Processed users:', users);
      return users;
    } catch (error) {
      console.error('Error in getAll users:', error);
      throw error;
    }
  },

  getById: async (id: number): Promise<User> => {
    const response = await api.get(`/users/${id}/`);
    return response.data;
  },

  getByDepartment: async (departmentId: number): Promise<User[]> => {
    try {
      console.log('Fetching users for department:', departmentId);
      const response = await api.get(`/users/department_users/`, {
        params: { department: departmentId }
      });
      console.log('Department users API response:', response);
      
      // Handle different response structures
      let users: User[] = [];
      if (response.data) {
        if (Array.isArray(response.data)) {
          users = response.data as User[];
        } else if (response.data.results && Array.isArray(response.data.results)) {
          users = response.data.results as User[];
        } else if (typeof response.data === 'object') {
          // If it's a single user object, wrap it in an array
          users = [response.data as User];
        }
      }
      
      console.log('Processed department users:', users);
      return users;
    } catch (error) {
      console.error('Error in getByDepartment:', error);
      throw error;
    }
  },

  getByDepartmentUnit: async (unitId: number): Promise<User[]> => {
    try {
      console.log('Fetching users for department unit:', unitId);
      const response = await api.get(`/users/department_unit_users/`, {
        params: { department_unit: unitId }
      });
      console.log('Department unit users API response:', response);
      
      // Handle different response structures
      let users: User[] = [];
      if (response.data) {
        if (Array.isArray(response.data)) {
          users = response.data as User[];
        } else if (response.data.results && Array.isArray(response.data.results)) {
          users = response.data.results as User[];
        } else if (typeof response.data === 'object') {
          // If it's a single user object, wrap it in an array
          users = [response.data as User];
        }
      }
      
      console.log('Processed department unit users:', users);
      return users;
    } catch (error) {
      console.error('Error in getByDepartmentUnit:', error);
      throw error;
    }
  },

  create: async (user: Partial<User>): Promise<User> => {
    const response = await api.post('/users/', user);
    return response.data;
  },

  update: async (id: number, user: Partial<User>): Promise<User> => {
    const response = await api.patch(`/users/${id}/`, user);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/users/${id}/`);
  }
}; 