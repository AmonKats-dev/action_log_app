export const ROLES = {
  ECONOMIST: 'economist',
  SENIOR_ECONOMIST: 'senior_economist',
  PRINCIPAL_ECONOMIST: 'principal_economist',
  ASSISTANT_COMMISSIONER: 'assistant_commissioner',
  COMMISSIONER: 'commissioner',
  SUPER_ADMIN: 'super_admin'
} as const;

export interface Role {
  id: number;
  name: 'ECONOMIST' | 'SENIOR_ECONOMIST' | 'PRINCIPAL_ECONOMIST' | 'ASSISTANT_COMMISSIONER' | 'COMMISSIONER' | 'SUPER_ADMIN';
  can_create_logs: boolean;
  can_update_status: boolean;
  can_approve: boolean;
  can_view_all_logs: boolean;
  can_configure: boolean;
  can_view_all_users: boolean;
  can_assign_to_commissioner: boolean;
}

export type RoleType = typeof ROLES[keyof typeof ROLES];

export const ROLE_HIERARCHY = {
  [ROLES.ECONOMIST]: 1,
  [ROLES.SENIOR_ECONOMIST]: 2,
  [ROLES.PRINCIPAL_ECONOMIST]: 3,
  [ROLES.ASSISTANT_COMMISSIONER]: 4,
  [ROLES.COMMISSIONER]: 5,
  [ROLES.SUPER_ADMIN]: 6,
} as const;

export const hasRequiredRole = (userRole: RoleType, requiredRole: RoleType): boolean => {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[requiredRole];
};

const MANAGER_ROLES = [ROLES.COMMISSIONER, ROLES.ASSISTANT_COMMISSIONER, ROLES.SUPER_ADMIN] as const;
const CONFIG_ROLES = [ROLES.COMMISSIONER, ROLES.SUPER_ADMIN] as const;
const APPROVER_ROLES = [
  ROLES.SENIOR_ECONOMIST,
  ROLES.PRINCIPAL_ECONOMIST,
  ROLES.ASSISTANT_COMMISSIONER,
  ROLES.COMMISSIONER,
  ROLES.SUPER_ADMIN
] as const;

export const canManageUsers = (role: RoleType): boolean => {
  return MANAGER_ROLES.includes(role as typeof MANAGER_ROLES[number]);
};

export const canConfigure = (role: RoleType): boolean => {
  return CONFIG_ROLES.includes(role as typeof CONFIG_ROLES[number]);
};

export const canApprove = (role: RoleType): boolean => {
  return APPROVER_ROLES.includes(role as typeof APPROVER_ROLES[number]);
}; 