import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { actionLogService } from '../services/actionLogService';
import { departmentService, DepartmentUnit } from '../services/departmentService';
import { userService } from '../services/userService';
import { ActionLog, ActionLogStatus } from '../types/actionLog';
import { Department } from '../types/department';
import { Button, Card, Table, Modal, Form, Input, message, Space, Tag, Select, DatePicker, Layout, Menu, Avatar, Tooltip, Timeline, Spin, Badge } from 'antd';
import { PlusOutlined, CheckOutlined, FilterOutlined, UserAddOutlined, UserOutlined, FileTextOutlined, FormOutlined, TeamOutlined, SettingOutlined } from '@ant-design/icons';
import { format } from 'date-fns';
import './ActionLogs/economistDashboard.css';
import { Navigate, useNavigate } from 'react-router-dom';
import { User } from '../types/user';
import { Dayjs } from 'dayjs';

const { Sider, Content } = Layout;

const priorities = [
  { label: 'Low', value: 'Low' },
  { label: 'Medium', value: 'Medium' },
  { label: 'High', value: 'High' },
];

const statuses = [
  { label: 'All Statuses', value: '' },
  { label: 'Open', value: 'open' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Closed', value: 'closed' },
];

const mockUsers = [
  'John Doe',
  'Jane Smith',
  'Mike Johnson',
  'Sarah Williams',
];

const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [actionLogs, setActionLogs] = useState<ActionLog[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [departmentUnits, setDepartmentUnits] = useState<DepartmentUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [unitsLoading, setUnitsLoading] = useState(true);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [assignModalVisible, setAssignModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<ActionLog | null>(null);
  const [form] = Form.useForm();
  const [assignForm] = Form.useForm();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedMenuKey, setSelectedMenuKey] = useState('actionLogs');
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [selectedDepartmentUnit, setSelectedDepartmentUnit] = useState<string | number | null>(null);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [statusModalVisible, setStatusModalVisible] = useState(false);
  const [statusForm] = Form.useForm();
  const [currentLogId, setCurrentLogId] = useState<number | null>(null);
  const [currentStatus, setCurrentStatus] = useState<ActionLogStatus | null>(null);
  const [commentsModalVisible, setCommentsModalVisible] = useState(false);
  const [selectedLogComments, setSelectedLogComments] = useState<any[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [readComments, setReadComments] = useState<Set<number>>(() => {
    // Initialize from localStorage
    const saved = localStorage.getItem('readComments');
    return saved ? new Set(JSON.parse(saved)) : new Set();
  });

  // Save read comments to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('readComments', JSON.stringify(Array.from(readComments)));
  }, [readComments]);

  useEffect(() => {
    const initializeData = async () => {
      try {
        console.log('Initializing dashboard data...');
        console.log('Current user:', user);
        
        // First fetch departments and units
        await Promise.all([
          fetchDepartments(),
          fetchDepartmentUnits()
        ]);
        
        // Then fetch action logs and all users
        await Promise.all([
          fetchActionLogs(),
          fetchAllUsers() // Fetch all users initially
        ]);
      } catch (error) {
        console.error('Error initializing data:', error);
        message.error('Failed to initialize dashboard data');
      }
    };
    initializeData();
  }, []);

  const fetchActionLogs = async () => {
    try {
      console.log('Fetching action logs...');
      const response = await actionLogService.getAll();
      console.log('Fetched action logs:', response);
      
      // Handle paginated response
      const logs = response.results || response;
      console.log('Processed logs:', logs);
      
      // Ensure we have an array of logs
      const logsArray = Array.isArray(logs) ? logs : [];
      
      // Update action logs state
      setActionLogs(logsArray);
      
      // Update read comments state for new logs
      const newReadComments = new Set(readComments);
      logsArray.forEach(log => {
        if (log.comments) {
          log.comments.forEach((comment: any) => {
            if (comment.user?.id !== user.id) {
              newReadComments.add(comment.id);
            }
          });
        }
      });
      setReadComments(newReadComments);
    } catch (error) {
      console.error('Error fetching action logs:', error);
      message.error('Failed to fetch action logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchDepartments = async () => {
    try {
      const response = await departmentService.getAll();
      console.log('Departments API response:', JSON.stringify(response, null, 2));
      
      // Handle the response data
      let departmentsData: Department[] = [];
      
      if (Array.isArray(response)) {
        departmentsData = response;
      } else if (response && typeof response === 'object') {
        // Type the response object
        interface PaginatedResponse {
          results?: Department[];
        }
        const typedResponse = response as PaginatedResponse;
        departmentsData = Array.isArray(typedResponse.results) ? typedResponse.results : [];
      }
      
      console.log('Processed departments:', JSON.stringify(departmentsData, null, 2));
      setDepartments(departmentsData);
    } catch (error) {
      console.error('Error fetching departments:', error);
      message.error('Failed to fetch departments');
      setDepartments([]);
    }
  };

  const fetchDepartmentUnits = async () => {
    try {
      setUnitsLoading(true);
      const units = await departmentService.getUnits();
      console.log('Fetched department units:', units);
      
      if (!Array.isArray(units)) {
        console.warn('Expected array of units but got:', units);
        setDepartmentUnits([]);
        return;
      }
      
      setDepartmentUnits(units);
    } catch (error) {
      console.error('Error fetching department units:', error);
      message.error('Failed to fetch department units');
      setDepartmentUnits([]);
    } finally {
      setUnitsLoading(false);
    }
  };

  const fetchAllUsers = async () => {
    try {
      const data = await userService.getByDepartment(user.department);
      const usersArray = Array.isArray(data) ? data.filter(user => user.is_active) : [];
      setAllUsers(usersArray);
      setUsers(usersArray); // Also set the filtered users initially
    } catch (error) {
      console.error('Error fetching all users:', error);
      message.error('Failed to fetch users');
    }
  };

  const fetchUsers = async (unitId: string | number) => {
    try {
      setUsersLoading(true);
      let users: User[] = [];
      
      if (unitId === 'all') {
        // If user has permission to view all users, fetch all users
        if (user.role?.can_view_all_users) {
          users = await userService.getAll();
        } else {
          // Otherwise fetch users from their department
          users = await userService.getByDepartment(user.department);
        }
      } else {
        // Fetch users from specific unit
        users = await userService.getByDepartmentUnit(Number(unitId));
      }
      
      setUsers(users);
    } catch (error) {
      console.error('Error fetching users:', error);
      message.error('Failed to fetch users');
    } finally {
      setUsersLoading(false);
    }
  };

  const renderDepartmentUnitOptions = () => {
    const options = [
      { label: 'All', value: 'all', key: 'all' }
    ];

    // Add specific units from the user's department
    if (departments.length > 0) {
      const userDepartment = departments.find(dept => dept.id === user.department);
      if (userDepartment?.units) {
        // If user is commissioner or assistant commissioner, show all units
        if (user.role?.can_view_all_users) {
          const unitOptions = userDepartment.units.map(unit => ({
            label: unit.name,
            value: unit.id.toString(),
            key: `unit-${unit.id}`
          }));
          options.push(...unitOptions);
        } else {
          // For department unit heads, only show their unit
          const userUnit = userDepartment.units.find(unit => unit.id === user.department_unit?.id);
          if (userUnit) {
            options.push({
              label: userUnit.name,
              value: userUnit.id.toString(),
              key: `unit-${userUnit.id}`
            });
          }
        }
      }
    }
    
    console.log('Department/Unit options:', options);
    return options;
  };

  const handleDepartmentChange = (value: string | number) => {
    console.log('Department changed to:', value);
    console.log('Current user department:', user.department);
    
    // If user is not commissioner or assistant commissioner, only allow viewing their own unit
    if (!user.role?.can_view_all_users) {
      if (value !== 'all') {
        const selectedUnit = departmentUnits.find(unit => unit.id.toString() === value.toString());
        if (selectedUnit && selectedUnit.id !== user.department_unit?.id) {
          message.warning('You can only view users in your own unit');
          return;
        }
      }
    }
    
    // Update selected unit and fetch users
    setSelectedDepartmentUnit(value);
    fetchUsers(value);
  };

  const handleCreate = async (values: any) => {
    try {
      console.log('Creating action log with values:', JSON.stringify(values, null, 2));
      
      // Validate required fields
      if (!values.title || !values.description || !values.due_date || !values.priority || !values.department_id) {
        message.error('Please fill in all required fields');
        return;
      }

      // Validate assigned users
      if (!values.assigned_to || values.assigned_to.length === 0) {
        message.error('Please select at least one user to assign');
        return;
      }

      // Get the department ID from the selected unit
      let departmentId = user.department; // Default to user's department
      
      if (values.department_id !== 'all') {
        // Find the unit in the PAP department
        const papDepartment = departments[0];
        const selectedUnit = papDepartment.units?.find(unit => unit.id.toString() === values.department_id);
        
        if (selectedUnit) {
          departmentId = selectedUnit.department;
        } else {
          message.error('Selected unit does not exist. Please select a valid unit.');
          return;
        }
      }
      
      const createData = {
        title: values.title,
        description: values.description,
        due_date: values.due_date?.toISOString(),
        priority: values.priority,
        status: 'open' as ActionLogStatus,
        department_id: departmentId,
        assigned_to: values.assigned_to.map((id: string) => Number(id))
      };

      console.log('Submitting action log data:', JSON.stringify(createData, null, 2));
      
      const response = await actionLogService.create(createData);
      console.log('Create response:', JSON.stringify(response, null, 2));
      
      message.success('Action log created successfully');
      setCreateModalVisible(false);
      form.resetFields();
      setSelectedDepartmentUnit(null);
      fetchActionLogs(); // Refresh the action logs list
    } catch (error: any) {
      console.error('Error creating action log:', error);
      if (error.response?.data) {
        console.error('Error details:', JSON.stringify(error.response.data, null, 2));
        
        // Handle different error response formats
        let errorMessage = 'Failed to create action log. Please try again.';
        
        if (typeof error.response.data === 'string') {
          errorMessage = error.response.data;
        } else if (typeof error.response.data === 'object') {
          // Handle object with field errors
          const errorEntries = Object.entries(error.response.data);
          if (errorEntries.length > 0) {
            errorMessage = errorEntries
              .map(([field, message]) => {
                if (Array.isArray(message)) {
                  return `${field}: ${message.join(', ')}`;
                }
                return `${field}: ${message}`;
              })
              .join('\n');
          }
        }
        
        message.error(errorMessage);
      } else {
        message.error('Failed to create action log. Please try again.');
      }
    }
  };

  const handleAssign = async (values: any) => {
    try {
      if (!selectedLog) return;
      
      // Check if user has permission to assign to commissioner
      if (values.assigned_to) {
        const assignedUser = users.find(u => u.id === values.assigned_to);
        if (assignedUser?.role?.name === 'commissioner' && !user.role?.can_assign_to_commissioner) {
          message.error('You do not have permission to assign to commissioner');
          return;
        }
      }
      
      await actionLogService.update(selectedLog.id, {
        assigned_to: values.assigned_to
      });
      message.success('Action log assigned successfully');
      setAssignModalVisible(false);
      assignForm.resetFields();
      fetchActionLogs();
    } catch (error) {
      console.error('Error assigning action log:', error);
      message.error('Failed to assign action log');
    }
  };

  const handleStatusUpdate = async (logId: number, newStatus: ActionLogStatus) => {
    setCurrentLogId(logId);
    setCurrentStatus(newStatus);
    setStatusModalVisible(true);
  };

  const handleStatusSubmit = async (values: any) => {
    if (!currentLogId || !currentStatus) return;

    try {
      const updateData = {
        status: currentStatus,
        comment: values.comment
      };

      await actionLogService.update(currentLogId, updateData);
      
      // Only show approval option if status is 'closed'
      if (currentStatus === 'closed' && canApprove) {
        message.success('Status updated. Please approve the action log.');
      } else {
        message.success('Status updated successfully');
      }
      
      setStatusModalVisible(false);
      statusForm.resetFields();
      fetchActionLogs();
    } catch (error) {
      message.error('Failed to update status');
    }
  };

  const handleApprove = async (logId: number) => {
    try {
      const log = actionLogs.find(l => l.id === logId);
      if (!log) {
        message.error('Action log not found');
        return;
      }

      if (log.status !== 'closed') {
        message.warning('Only closed action logs can be approved');
        return;
      }

      await actionLogService.approve(logId);
      message.success('Action log approved successfully');
      fetchActionLogs();
    } catch (error) {
      message.error('Failed to approve action log');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'blue';
      case 'in_progress':
        return 'orange';
      case 'closed':
        return 'green';
      default:
        return 'default';
    }
  };

  if (!user) return <Navigate to="/login" replace />;

  // Debug: Log the user object to the console
  console.log('User object:', user);
  console.log('User role:', user?.role);
  console.log('User department:', user?.department);
  console.log('User permissions:', user?.permissions);

  const getFullName = (user: any) => {
    const first = user.first_name?.trim() || '';
    const last = user.last_name?.trim() || '';
    const full = `${first} ${last}`.trim();
    return full || user.username;
  };

  const isSeniorEconomist = user.role?.name === 'senior_economist';
  const isPrincipalEconomist = user.role?.name === 'principal_economist';
  const isAssistantCommissioner = user.role?.name === 'assistant_commissioner';
  const isCommissioner = user.role?.name === 'commissioner';
  const isSuperAdmin = user.role?.name === 'super_admin';

  const canAssign = user.role?.can_update_status || false;
  const canUpdateStatus = user.role?.can_update_status || false;
  const canApprove = user.role?.can_approve || false;
  const canConfigure = user.role?.can_configure || false;
  const canCreateLogs = user.role?.can_create_logs || false;
  const canViewAllLogs = user.role?.can_view_all_logs || false;

  const getDashboardTitle = () => {
    if (isSuperAdmin) return 'Super Admin Dashboard';
    if (isCommissioner) return 'Commissioner Dashboard';
    if (isAssistantCommissioner) return 'Assistant Commissioner Dashboard';
    if (isPrincipalEconomist) return 'Principal Economist Dashboard';
    if (isSeniorEconomist) return 'Senior Economist Dashboard';
    return 'Economist Dashboard';
  };

  // Filter and search logic
  const filteredLogs = Array.isArray(actionLogs)
    ? actionLogs.filter(log => {
        const matchesSearch =
          log.title.toLowerCase().includes(search.toLowerCase()) ||
          log.description.toLowerCase().includes(search.toLowerCase());
        const matchesStatus = statusFilter ? log.status === statusFilter : true;
        return matchesSearch && matchesStatus;
      })
    : [];

  // Debug: Log the filtered logs
  console.log('Filtered logs:', filteredLogs);

  const renderAssignedUsers = (assigned: any[], record: ActionLog) => {
    // Use allUsers instead of users for displaying assigned users
    const assignedUsers = allUsers.filter(user => 
      assigned.some(id => id.toString() === user.id.toString())
    );
    
    return (
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <div style={{
          color: '#333',
          fontSize: '14px',
          lineHeight: '1.4'
        }}>
          {assignedUsers.length > 0 ? (
            assignedUsers.map(user => `${user.first_name} ${user.last_name}`).join(', ')
          ) : (
            <span style={{ color: '#999', fontStyle: 'italic' }}>Unassigned</span>
          )}
        </div>
        {canAssign && (
          <Button 
            type="link" 
            icon={<TeamOutlined />} 
            onClick={() => {
              setSelectedLog(record);
              setAssignModalVisible(true);
            }}
            style={{
              padding: 0,
              height: 'auto',
              fontSize: '13px'
            }}
          >
            Assign
          </Button>
        )}
      </Space>
    );
  };

  const fetchComments = async (logId: number) => {
    try {
      setCommentsLoading(true);
      const response = await actionLogService.getComments(logId);
      
      // Handle paginated response
      const comments = response.results || response;
      
      // Sort comments by date, newest first
      const sortedComments = Array.isArray(comments) 
        ? comments.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        : [];
      
      setSelectedLogComments(sortedComments);
      
      // Mark comments as read only if they are not from the current user
      const newReadComments = new Set(readComments);
      sortedComments.forEach(comment => {
        if (comment.user?.id !== user.id) {
          newReadComments.add(comment.id);
        }
      });
      setReadComments(newReadComments);
    } catch (error) {
      console.error('Error fetching comments:', error);
      message.error('Failed to fetch comments');
    } finally {
      setCommentsLoading(false);
    }
  };

  const handleViewComments = async (logId: number) => {
    setSelectedLog(actionLogs.find(log => log.id === logId) || null);
    await fetchComments(logId);
    setCommentsModalVisible(true);
  };

  const handleAddComment = async () => {
    if (!selectedLog || !newComment.trim()) return;

    try {
      setSubmittingComment(true);
      const response = await actionLogService.update(selectedLog.id, {
        status: selectedLog.status,
        comment: newComment.trim()
      });
      
      message.success('Comment added successfully');
      setNewComment('');
      
      // Fetch updated comments and refresh the action logs list
      await Promise.all([
        fetchComments(selectedLog.id),
        fetchActionLogs()
      ]);
    } catch (error) {
      console.error('Error adding comment:', error);
      message.error('Failed to add comment');
    } finally {
      setSubmittingComment(false);
    }
  };

  const columns = [
    {
      title: 'TITLE',
      dataIndex: 'title',
      key: 'title',
      width: '20%',
      render: (text: string) => (
        <div style={{ 
          fontWeight: 600,
          color: '#1a1a1a',
          fontSize: '14px',
          lineHeight: '1.4'
        }}>
          {text}
        </div>
      ),
    },
    {
      title: 'DESCRIPTION',
      dataIndex: 'description',
      key: 'description',
      width: '30%',
      render: (text: string) => (
        <div style={{ 
          whiteSpace: 'normal',
          wordBreak: 'break-word',
          color: '#333',
          fontSize: '14px',
          lineHeight: '1.5',
          maxHeight: '100px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          display: '-webkit-box',
          WebkitLineClamp: 3,
          WebkitBoxOrient: 'vertical'
        }}>
          {text}
        </div>
      ),
    },
    {
      title: 'STATUS',
      dataIndex: 'status',
      key: 'status',
      width: '15%',
      render: (status: ActionLogStatus, record: ActionLog) => (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Tag 
            color={getStatusColor(status)} 
            style={{ 
              fontWeight: 500,
              padding: '4px 8px',
              borderRadius: '4px',
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}
          >
            {status === 'open' ? 'Open' : status === 'in_progress' ? 'In Progress' : 'Closed'}
          </Tag>
          {canUpdateStatus && (
            <Select
              defaultValue={status}
              style={{ width: '100%' }}
              onChange={(value: ActionLogStatus) => handleStatusUpdate(record.id, value)}
              options={[
                { value: 'open' as ActionLogStatus, label: 'Open' },
                { value: 'in_progress' as ActionLogStatus, label: 'In Progress' },
                { value: 'closed' as ActionLogStatus, label: 'Closed' },
              ]}
            />
          )}
        </Space>
      ),
    },
    {
      title: 'DUE DATE',
      dataIndex: 'due_date',
      key: 'due_date',
      width: '12%',
      render: (date: string) => (
        <div style={{
          color: '#333',
          fontSize: '14px',
          fontWeight: 500
        }}>
          {date ? format(new Date(date), 'MMM dd, yyyy') : '-'}
        </div>
      ),
    },
    {
      title: 'ASSIGNED TO',
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      width: '15%',
      render: renderAssignedUsers
    },
    {
      title: 'ACTIONS',
      key: 'actions',
      width: '15%',
      render: (_: unknown, record: ActionLog) => {
        // Calculate unread comments - only count comments not from the current user
        const unreadComments = record.comment_count - 
          Array.from(readComments).filter(id => 
            selectedLogComments.some(comment => 
              comment.id === id && comment.user?.id !== user.id
            )
          ).length;

        return (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            {canUpdateStatus && (
              <Select
                value={record.status}
                style={{ width: '100%' }}
                onChange={(value: ActionLogStatus) => handleStatusUpdate(record.id, value)}
                options={[
                  { value: 'open', label: 'Open' },
                  { value: 'in_progress', label: 'In Progress' },
                  { value: 'closed', label: 'Closed' }
                ]}
              />
            )}
            {canAssign && (
              <Button 
                type="link" 
                icon={<TeamOutlined />} 
                onClick={() => {
                  setSelectedLog(record);
                  setAssignModalVisible(true);
                }}
                style={{
                  padding: 0,
                  height: 'auto',
                  fontSize: '13px'
                }}
              >
                Assign
              </Button>
            )}
            <Button 
              type="link" 
              icon={<FileTextOutlined />} 
              onClick={() => handleViewComments(record.id)}
              style={{
                padding: 0,
                height: 'auto',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              View Comments
              {unreadComments > 0 && (
                <Badge 
                  count={unreadComments} 
                  size="small" 
                  style={{ 
                    backgroundColor: '#1890ff',
                    marginLeft: '4px'
                  }} 
                />
              )}
            </Button>
            {canApprove && record.status === 'closed' && (
              <Button 
                type="link" 
                icon={<CheckOutlined />} 
                onClick={() => handleApprove(record.id)}
                style={{
                  padding: 0,
                  height: 'auto',
                  fontSize: '13px'
                }}
              >
                Approve
              </Button>
            )}
          </Space>
        );
      },
    },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleMenuClick = (e: any) => {
    setSelectedMenuKey(e.key);
    if (e.key === 'createActionLog') {
      setCreateModalVisible(true);
    }
    if (e.key === 'logout') {
      handleLogout();
    }
  };

  const renderUserOptions = () => {
    if (!Array.isArray(users)) {
      console.warn('Users is not an array:', users);
      return [];
    }
    
    return users.map(user => ({
      label: `${user.first_name} ${user.last_name}`,
      value: user.id.toString(),
      key: `user-${user.id}`
    }));
  };

  const menuItems = [
    {
      key: 'actionLogs',
      icon: <FileTextOutlined />,
      label: 'Action Logs',
    },
    ...(canCreateLogs ? [{
      key: 'createActionLog',
      icon: <FormOutlined />,
      label: 'Create Action Log',
    }] : []),
    ...(canConfigure ? [{
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    }] : []),
    {
      key: 'logout',
      icon: <UserOutlined />,
      label: 'Logout',
      style: { marginTop: 32, color: '#d32f2f' },
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh', height: '100vh', overflow: 'hidden' }}>
      <Sider width={240} style={{ background: '#fff', boxShadow: '2px 0 8px #f0f1f2' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '32px 0 16px 0' }}>
          <Avatar size={64} icon={<UserOutlined />} style={{ marginBottom: 12 }} />
          <div style={{ fontWeight: 500, fontSize: 14, color: '#888', marginBottom: 4 }}>Logged in as:</div>
          <div style={{ fontWeight: 700, fontSize: 20, marginBottom: 2, color: '#222', textAlign: 'center', letterSpacing: 0.5 }}>
            {getFullName(user)}
          </div>
          <div style={{ fontWeight: 400, fontSize: 15, color: '#2563eb', marginBottom: 20 }}>
            {user.role?.name ? user.role.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : ''}
          </div>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedMenuKey]}
          onClick={handleMenuClick}
          style={{ borderRight: 0, fontSize: 16 }}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Content style={{ padding: 0, margin: 0, minHeight: '100vh', background: 'transparent' }}>
          <div className="economist-dashboard-bg" style={{ height: '100vh', overflow: 'hidden' }}>
            <Card className="economist-dashboard-header">
              <div className="dashboard-header-content">
                <div className="dashboard-title-row">
                  <UserAddOutlined style={{ fontSize: 32 }} />
                  <span className="dashboard-title">
                    {getDashboardTitle()}
                  </span>
                </div>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  size="large"
                  className="create-action-log-btn"
                  onClick={() => setCreateModalVisible(true)}
                >
                  Create Action Log
                </Button>
              </div>
            </Card>

            <Card className="economist-dashboard-search-card">
              <div className="dashboard-search-row">
                <Input
                  placeholder="Search action logs..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="dashboard-search-input"
                  allowClear
                  prefix={<UserAddOutlined />}
                />
                <Button icon={<FilterOutlined />} className="dashboard-filter-btn" />
                <Select
                  value={statusFilter}
                  onChange={setStatusFilter}
                  options={statuses}
                  className="dashboard-status-select"
                />
              </div>
            </Card>

            <Card 
              className="economist-dashboard-table-card"
              style={{
                margin: '16px',
                borderRadius: '8px',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)'
              }}
            >
              <Table
                columns={columns}
                dataSource={filteredLogs}
                loading={loading}
                rowKey="id"
                pagination={false}
                className="dashboard-table"
                scroll={{ y: 'calc(100vh - 400px)' }}
                locale={{
                  emptyText: 'No action logs found'
                }}
                style={{
                  fontSize: '14px'
                }}
                rowClassName={() => 'dashboard-table-row'}
                onRow={(record) => ({
                  style: {
                    backgroundColor: '#fff',
                    transition: 'background-color 0.3s'
                  }
                })}
              />
            </Card>

            <Modal
              title={<span className="modal-title">Create New Action Log</span>}
              open={createModalVisible}
              onCancel={() => {
                setCreateModalVisible(false);
                form.resetFields();
                setSelectedDepartmentUnit(null);
              }}
              footer={null}
              width={600}
              className="dashboard-modal"
            >
              <Form 
                form={form} 
                onFinish={handleCreate} 
                layout="vertical"
                initialValues={{
                  priority: 'Medium'
                }}
              >
                <div className="modal-row">
                  <Form.Item
                    name="title"
                    label="Title"
                    className="modal-form-item"
                    rules={[
                      { required: true, message: 'Enter action log title' },
                      { max: 100, message: 'Title cannot exceed 100 characters' }
                    ]}
                  >
                    <Input placeholder="Enter action log title" />
                  </Form.Item>
                  <Form.Item
                    name="department_id"
                    label="Departmental Unit"
                    className="modal-form-item"
                    rules={[{ required: true, message: 'Select a department unit' }]}
                  >
                    <Select
                      placeholder="Select unit"
                      options={renderDepartmentUnitOptions()}
                      loading={unitsLoading}
                      onChange={handleDepartmentChange}
                    />
                  </Form.Item>
                </div>
                <Form.Item
                  name="description"
                  label="Description"
                  className="modal-form-item"
                  rules={[
                    { required: true, message: 'Provide detailed description of the action item' },
                    { min: 10, message: 'Description must be at least 10 characters' }
                  ]}
                >
                  <Input.TextArea 
                    rows={4} 
                    placeholder="Provide detailed description of the action item"
                    maxLength={500}
                    showCount
                  />
                </Form.Item>
                <div className="modal-row">
                  <Form.Item
                    name="due_date"
                    label="Due Date"
                    className="modal-form-item"
                    rules={[
                      { required: true, message: 'Select due date' },
                      { type: 'object', message: 'Please select a valid date' }
                    ]}
                  >
                    <DatePicker 
                      style={{ width: '100%' }} 
                      placeholder="mm/dd/yyyy"
                      disabledDate={(current: Dayjs) => {
                        return current && current.isBefore(new Date().setHours(0, 0, 0, 0));
                      }}
                    />
                  </Form.Item>
                  <Form.Item
                    name="priority"
                    label="Priority"
                    className="modal-form-item"
                    rules={[{ required: true, message: 'Select priority' }]}
                  >
                    <Select options={priorities} placeholder="Select priority" />
                  </Form.Item>
                </div>
                <Form.Item
                  name="assigned_to"
                  label="Assign To"
                  className="modal-form-item"
                  rules={[
                    { required: true, message: 'Select at least one assignee' },
                    { type: 'array', min: 1, message: 'Select at least one assignee' }
                  ]}
                >
                  <Select
                    mode="multiple"
                    placeholder={selectedDepartmentUnit ? "Select users" : "Select a department unit first"}
                    options={renderUserOptions()}
                    loading={usersLoading}
                    style={{ minHeight: 80 }}
                    disabled={!selectedDepartmentUnit}
                    allowClear
                  />
                </Form.Item>
                <div className="modal-footer-row">
                  <Button 
                    onClick={() => {
                      setCreateModalVisible(false);
                      form.resetFields();
                      setSelectedDepartmentUnit(null);
                    }} 
                    className="modal-cancel-btn"
                  >
                    Cancel
                  </Button>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    className="modal-create-btn"
                    loading={loading}
                  >
                    Create Action Log
                  </Button>
                </div>
              </Form>
            </Modal>

            <Modal
              title={<span className="modal-title">Assign Action Log</span>}
              open={assignModalVisible}
              onCancel={() => setAssignModalVisible(false)}
              footer={null}
              width={500}
              className="dashboard-modal"
            >
              <Form form={assignForm} onFinish={handleAssign} layout="vertical">
                <Form.Item
                  name="assigned_to"
                  label="Assign To"
                  rules={[{ required: true, message: 'Select at least one assignee' }]}
                >
                  <Select
                    mode="multiple"
                    placeholder="Select economists"
                    options={mockUsers.map(name => ({ label: name, value: name }))}
                    style={{ minHeight: 80 }}
                  />
                </Form.Item>
                <div className="modal-footer-row">
                  <Button onClick={() => setAssignModalVisible(false)} className="modal-cancel-btn">
                    Cancel
                  </Button>
                  <Button type="primary" htmlType="submit" className="modal-create-btn">
                    Assign
                  </Button>
                </div>
              </Form>
            </Modal>

            <Modal
              title={<span className="modal-title">Update Status</span>}
              open={statusModalVisible}
              onCancel={() => {
                setStatusModalVisible(false);
                statusForm.resetFields();
              }}
              footer={null}
              width={500}
              className="dashboard-modal"
            >
              <Form form={statusForm} onFinish={handleStatusSubmit} layout="vertical">
                <Form.Item
                  name="comment"
                  label="Comment"
                  rules={[
                    { required: true, message: 'Please provide a comment for the status change' },
                    { min: 10, message: 'Comment must be at least 10 characters' }
                  ]}
                >
                  <Input.TextArea 
                    rows={4} 
                    placeholder="Provide a comment explaining the status change"
                    maxLength={500}
                    showCount
                  />
                </Form.Item>
                <div className="modal-footer-row">
                  <Button 
                    onClick={() => {
                      setStatusModalVisible(false);
                      statusForm.resetFields();
                    }} 
                    className="modal-cancel-btn"
                  >
                    Cancel
                  </Button>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    className="modal-create-btn"
                  >
                    Update Status
                  </Button>
                </div>
              </Form>
            </Modal>

            <Modal
              title={
                <div className="modal-title">
                  <span>Comments History</span>
                  {selectedLog && (
                    <div style={{ fontSize: '14px', color: '#666', marginTop: '4px' }}>
                      {selectedLog.title}
                    </div>
                  )}
                </div>
              }
              open={commentsModalVisible}
              onCancel={() => {
                setCommentsModalVisible(false);
                setNewComment('');
              }}
              footer={null}
              width={600}
              className="dashboard-modal"
            >
              <div style={{ 
                display: 'flex', 
                flexDirection: 'column',
                height: '60vh'
              }}>
                <div style={{ 
                  flex: 1,
                  overflowY: 'auto',
                  marginBottom: '16px',
                  padding: '0 4px'
                }}>
                  {commentsLoading ? (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                      <Spin />
                    </div>
                  ) : selectedLogComments.length > 0 ? (
                    <Timeline
                      items={selectedLogComments.map(comment => ({
                        color: comment.status === 'closed' ? 'green' : 
                               comment.status === 'in_progress' ? 'orange' : 'blue',
                        children: (
                          <div style={{ marginBottom: '16px' }}>
                            <div style={{ 
                              display: 'flex', 
                              justifyContent: 'space-between',
                              marginBottom: '8px'
                            }}>
                              <div style={{ fontWeight: 500 }}>
                                {comment.user?.first_name} {comment.user?.last_name}
                              </div>
                              <div style={{ color: '#666' }}>
                                {format(new Date(comment.created_at), 'MMM dd, yyyy HH:mm')}
                              </div>
                            </div>
                            <div style={{ 
                              backgroundColor: '#f5f5f5',
                              padding: '12px',
                              borderRadius: '4px',
                              marginBottom: '4px'
                            }}>
                              {comment.comment}
                            </div>
                            <div style={{ 
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              marginTop: '4px'
                            }}>
                              <Tag color={
                                comment.status === 'closed' ? 'green' :
                                comment.status === 'in_progress' ? 'orange' : 'blue'
                              }>
                                {comment.status === 'open' ? 'Open' :
                                 comment.status === 'in_progress' ? 'In Progress' : 'Closed'}
                              </Tag>
                              {comment.is_approved && (
                                <Tag color="green" icon={<CheckOutlined />}>
                                  Approved
                                </Tag>
                              )}
                            </div>
                          </div>
                        )
                      }))}
                    />
                  ) : (
                    <div style={{ 
                      textAlign: 'center', 
                      padding: '20px',
                      color: '#666'
                    }}>
                      No comments yet
                    </div>
                  )}
                </div>
                
                <div style={{ 
                  borderTop: '1px solid #f0f0f0',
                  paddingTop: '16px'
                }}>
                  <Form.Item
                    style={{ marginBottom: 0 }}
                    rules={[
                      { required: true, message: 'Please enter a comment' },
                      { min: 10, message: 'Comment must be at least 10 characters' }
                    ]}
                  >
                    <Input.TextArea
                      value={newComment}
                      onChange={e => setNewComment(e.target.value)}
                      placeholder="Add a new comment..."
                      rows={3}
                      maxLength={500}
                      showCount
                      style={{ marginBottom: '8px' }}
                    />
                  </Form.Item>
                  <div style={{ 
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '8px'
                  }}>
                    <Button 
                      onClick={() => {
                        setCommentsModalVisible(false);
                        setNewComment('');
                      }}
                    >
                      Close
                    </Button>
                    <Button
                      type="primary"
                      onClick={handleAddComment}
                      loading={submittingComment}
                      disabled={!newComment.trim() || newComment.trim().length < 10}
                    >
                      Add Comment
                    </Button>
                  </div>
                </div>
              </div>
            </Modal>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default Dashboard; 