import { User } from './user';
import { Department } from './department';

export type ActionLogStatus = 'open' | 'in_progress' | 'closed';
export type ActionLogPriority = 'High' | 'Medium' | 'Low';
export type ApprovalStatus = 'unit_head_approved' | 'assistant_commissioner_approved' | 'commissioner_approved' | null;

export interface ActionLog {
  id: number;
  title: string;
  description: string;
  department: {
    id: number;
    name: string;
    code: string;
    description: string;
    units: Array<{
      id: number;
      name: string;
      unit_type: string;
      description: string;
      department: number;
      department_name: string;
      created_at: string;
      updated_at: string;
    }>;
    created_at: string;
    updated_at: string;
  };
  created_by: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    role: {
      id: number;
      name: string;
      can_create_logs: boolean;
      can_update_status: boolean;
      can_approve: boolean;
      can_view_all_logs: boolean;
      can_configure: boolean;
    };
    department: number;
    department_unit: {
      id: number;
      name: string;
      unit_type: string;
      description: string;
      department: number;
      department_name: string;
      created_at: string;
      updated_at: string;
    };
    employee_id: string;
    phone_number: string;
    is_active: boolean;
    designation: string;
  };
  status: ActionLogStatus;
  priority: ActionLogPriority;
  due_date: string;
  assigned_to: number[];
  approved_by: number | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
  can_approve: boolean;
  comment_count: number;
  approval_status: ApprovalStatus;
}

export interface ActionLogComment {
  id: number;
  action_log: number;
  user: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
  };
  comment: string;
  created_at: string;
  updated_at: string;
  parent_id?: number | null;
  replies?: ActionLogComment[];
}

export interface ActionLogUpdate {
  title?: string;
  description?: string;
  status?: ActionLogStatus;
  priority?: string;
  due_date?: string;
  assigned_to?: number[];
  comment?: string;
  approval_status?: ApprovalStatus;
}

export interface CreateActionLogData {
  title: string;
  description: string;
  due_date: string | null;
  priority: string;
  department_id: number;
  department_unit: number;
  created_by: number;
  assigned_to: number[];
  status: ActionLogStatus;
}

export interface RejectActionLogData {
  reason: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
} 