import { Role } from '../constants/roles';
import { Department } from './department';
import { DepartmentUnit } from './department';

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  department: number;
  department_unit?: DepartmentUnit;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  designation?: string;
} 