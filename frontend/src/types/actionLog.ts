import { User } from './user';
import { Department } from './department';

export type ActionLogStatus = 'open' | 'in_progress' | 'pending_approval' | 'closed';
export type ActionLogPriority = 'High' | 'Medium' | 'Low';
export type ApprovalStatus = 'unit_head_approved' | 'assistant_commissioner_approved' | 'commissioner_approved' | null;

export interface ActionLog {
  id: number;
  title: string;
  description: string;
  department: Department;
  created_by: User;
  status: ActionLogStatus;
  priority: string;
  due_date: string | null;
  assigned_to: number[];
  approved_by: User | null;
  approved_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
  closure_approval_stage?: 'none' | 'unit_head' | 'assistant_commissioner' | 'commissioner' | 'closed' | 'rejected';
  closure_requested_by?: User | null;
  can_approve: boolean;
  comment_count: number;
  approval_status: ApprovalStatus;
  [key: string]: any;
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
  status?: ActionLogStatus;
  is_approved?: boolean;
  is_viewed?: boolean;
  parent_comment?: number | null;
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
  closure_approval_stage?: 'none' | 'unit_head' | 'assistant_commissioner' | 'commissioner' | 'closed' | 'rejected';
  closure_requested_by?: number | null;
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