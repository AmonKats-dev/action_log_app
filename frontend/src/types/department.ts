export interface Department {
  id: number;
  name: string;
  code: string;
  description: string;
  units: DepartmentUnit[];
  created_at: string;
  updated_at: string;
}

export interface DepartmentUnit {
  id: number;
  name: string;
  unit_type: string;
  description: string;
  department: number;
  department_name: string;
  created_at: string;
  updated_at: string;
} 