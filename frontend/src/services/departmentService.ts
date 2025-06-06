import { Department, DepartmentUnit } from '../types/department';
import { api } from './api';

export const departmentService = {
  getAll: async (): Promise<Department[]> => {
    const response = await api.get('/departments/');
    return response.data;
  },

  getById: async (id: number): Promise<Department> => {
    const response = await api.get(`/departments/${id}/`);
    return response.data;
  },

  getUnits: async (): Promise<DepartmentUnit[]> => {
    const response = await api.get('/departments/units/');
    return response.data;
  },

  getUnitsByDepartment: async (departmentId: number): Promise<DepartmentUnit[]> => {
    const response = await api.get(`/departments/${departmentId}/units/`);
    return response.data;
  }
}; 