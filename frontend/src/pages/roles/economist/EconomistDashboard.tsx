import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../auth/AuthContext';
import { actionLogService } from '../../../services/actionLogService';
import { departmentService } from '../../../services/departmentService';
import { userService } from '../../../services/userService';
import { ActionLog, ActionLogStatus, CreateActionLogData, ApprovalStatus, ActionLogUpdate } from '../../../types/actionLog';
import { Department, DepartmentUnit } from '../../../types/department';
import { Button, Card, Table, Modal, Form, Input, message, Space, Tag, Select, DatePicker, Layout, Menu, Avatar, Tooltip, Timeline, Spin, Badge, Tabs, Upload, List, Descriptions, Divider } from 'antd';
import { PlusOutlined, CheckOutlined, FilterOutlined, UserAddOutlined, UserOutlined, FileTextOutlined, FormOutlined, TeamOutlined, SettingOutlined, ClockCircleOutlined, CalendarOutlined, CommentOutlined, ClusterOutlined, UploadOutlined, HistoryOutlined, InfoCircleOutlined, PaperClipOutlined } from '@ant-design/icons';
import { format, differenceInDays, isPast, isToday } from 'date-fns';
import { Navigate, useNavigate } from 'react-router-dom';
import { User } from '../../../types/user';
import { Dayjs } from 'dayjs';
import UserDisplay from '../../../components/UserDisplay';
import { ColumnsType } from 'antd/es/table';
import * as XLSX from 'xlsx';

const { Sider, Content } = Layout;

interface Role {
  id: number;
  name: string;
  can_create_logs: boolean;
  can_update_status: boolean;
  can_approve: boolean;
  can_view_all_logs: boolean;
  can_configure: boolean;
  can_view_all_users: boolean;
  can_assign_to_commissioner: boolean;
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

interface DepartmentWithUnits extends Omit<Department, 'units'> {
  units: DepartmentUnit[];
}

interface CommentResponse {
  id: number;
  comment: string;
  user: {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
  };
  created_at: string;
  updated_at: string;
  status: ActionLogStatus;
  is_approved: boolean;
  replies?: CommentResponse[];
}

interface LocalActionLogComment {
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
  replies?: LocalActionLogComment[];
}

interface AssignmentHistory {
  id: number;
  assigned_by: {
    id: number;
    first_name: string;
    last_name: string;
  };
  assigned_to: Array<{
    id: number;
    first_name: string;
    last_name: string;
  }>;
  assigned_at: string;
  comment: string | null;
}

const EconomistDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [actionLogs, setActionLogs] = useState<ActionLog[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [departmentUnits, setDepartmentUnits] = useState<DepartmentUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedMenuKey, setSelectedMenuKey] = useState('actionLogs');
  const [showAssignedOnly, setShowAssignedOnly] = useState(false);
  const [commentsModalVisible, setCommentsModalVisible] = useState(false);
  const [selectedLogComments, setSelectedLogComments] = useState<LocalActionLogComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [userRole, setUserRole] = useState<Role | null>(null);
  const [selectedDepartmentUnit, setSelectedDepartmentUnit] = useState<string | number | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [selectedLog, setSelectedLog] = useState<ActionLog | null>(null);
  const [statusModalVisible, setStatusModalVisible] = useState(false);
  const [assignModalVisible, setAssignModalVisible] = useState(false);
  const [statusForm] = Form.useForm();
  const [currentLogId, setCurrentLogId] = useState<number | null>(null);
  const [currentStatus, setCurrentStatus] = useState<ActionLogStatus | null>(null);
  const [readComments, setReadComments] = useState<Set<number>>(new Set());
  const [replyingTo, setReplyingTo] = useState<CommentResponse | null>(null);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [selectedLogDetails, setSelectedLogDetails] = useState<ActionLog | null>(null);
  const [approvalModalVisible, setApprovalModalVisible] = useState(false);
  const [approvalForm] = Form.useForm();
  const [assignForm] = Form.useForm();
  const [createForm] = Form.useForm();
  const [assignmentHistory, setAssignmentHistory] = useState<AssignmentHistory[]>([]);

  // Add these variables at the component level
  const isUnitHead = user?.designation?.toLowerCase().includes('head') || 
                    (user?.designation?.match(/^[A-Z]{2,3}\d+\/PAP$/) && user?.designation?.toLowerCase().includes('1'));
  const isCommissioner = user?.role?.name?.toLowerCase() === 'commissioner';
  const isAssistantCommissioner = user?.role?.name?.toLowerCase() === 'assistant_commissioner';

  useEffect(() => {
    const initializeData = async () => {
      if (!user) {
        navigate('/login');
        return;
      }

      try {
        // Fetch all data in parallel
        const [departmentsData, unitsData, logsData, usersData] = await Promise.all([
          fetchDepartments(),
          fetchDepartmentUnits(),
          fetchActionLogs(),
          fetchUsers()
        ]);

        // Set the data only once
        setDepartments(departmentsData);
        setDepartmentUnits(unitsData);
        setActionLogs(logsData);
        setUsers(usersData);
      } catch (error) {
        console.error('Error initializing data:', error);
        message.error('Failed to initialize dashboard data');
      } finally {
        setLoading(false);
      }
    };
    initializeData();
  }, [user]);

  const fetchActionLogs = async () => {
    try {
      const response = await actionLogService.getAll();
      
      const logs = response.results || response;
      const logsArray = Array.isArray(logs) ? logs : [];
      
      // Filter logs based on user's role and unit
      const filteredLogs = logsArray.filter(log => {
        // If user is Commissioner or Assistant Commissioner, they can see all logs
        if (user?.role?.name?.toLowerCase() === 'commissioner' || 
            user?.role?.name?.toLowerCase() === 'assistant_commissioner') {
          return true;
        }
        
        // If user is a Unit Head, show logs from their unit or assigned to them
        const isUnitHead = user?.designation?.toLowerCase().includes('head') || 
                          (user?.designation?.match(/^[A-Z]{2,3}\d+\/PAP$/) && user?.designation?.toLowerCase().includes('1'));
        
        if (isUnitHead) {
          const isInUserUnit = log.created_by?.department_unit?.id === user?.department_unit?.id;
          const isAssignedToUser = log.assigned_to?.includes(user?.id);
          return isInUserUnit || isAssignedToUser;
        }
        
        // If user has no department unit, they can't see any logs
        if (!user?.department_unit) {
          return false;
        }
        
        // For other roles, check if the log was created in their unit or assigned to them
        const isInUserUnit = log.created_by?.department_unit?.id === user.department_unit.id;
        const isAssignedToUser = log.assigned_to?.includes(user.id);
        
        return isInUserUnit || isAssignedToUser;
      });

      return filteredLogs;
    } catch (error) {
      console.error('Error fetching action logs:', error);
      message.error('Failed to fetch action logs');
      return [];
    }
  };

  const fetchDepartments = async () => {
    try {
      const response = await departmentService.getAll();
      let departmentsData: Department[] = [];
      
      if (Array.isArray(response)) {
        departmentsData = response;
      } else if (response && typeof response === 'object') {
        const typedResponse = response as PaginatedResponse<Department>;
        departmentsData = Array.isArray(typedResponse.results) ? typedResponse.results : [];
      }
      
      return departmentsData;
    } catch (error) {
      console.error('Error fetching departments:', error);
      message.error('Failed to fetch departments');
      return [];
    }
  };

  const fetchDepartmentUnits = async () => {
    try {
      const response = await departmentService.getUnits();
      let units: DepartmentUnit[] = [];
      
      if (Array.isArray(response)) {
        units = response;
      } else if (response && typeof response === 'object') {
        const typedResponse = response as PaginatedResponse<DepartmentUnit>;
        if (Array.isArray(typedResponse.results)) {
          units = typedResponse.results;
        } else {
          console.warn('Unexpected response format:', response);
          units = [];
        }
      }
      
      return units;
    } catch (error) {
      console.error('Error fetching department units:', error);
      message.error('Failed to fetch department units');
      return [];
    }
  };

  const fetchUsers = async () => {
    if (!user) return [];

    try {
      setUsersLoading(true);
      const response = await userService.getByDepartment(user.department);
      let usersArray: User[] = [];
      
      if (Array.isArray(response)) {
        usersArray = response;
      } else if (response && typeof response === 'object') {
        const typedResponse = response as PaginatedResponse<User>;
        if (Array.isArray(typedResponse.results)) {
          usersArray = typedResponse.results;
        }
      }
      
      // Only filter out inactive users
      return usersArray.filter(user => user.is_active);
    } catch (error) {
      console.error('Error fetching users:', error);
      message.error('Failed to fetch users');
      return [];
    } finally {
      setUsersLoading(false);
    }
  };

  const getFilteredUsers = (currentUser: any) => {
    const isCommissioner = currentUser.role?.name?.toLowerCase() === 'commissioner';
    const isAssistantCommissioner = currentUser.role?.name?.toLowerCase() === 'assistant_commissioner';
    const isUnitHead = currentUser.designation?.toLowerCase().includes('head') || 
                      (currentUser.designation?.match(/^[A-Z]{2,3}\d+\/PAP$/) && currentUser.designation?.toLowerCase().includes('1'));

    return users.filter(u => {
      // No staff can assign themselves
      if (u.id === currentUser?.id) {
        return false;
      }
      // Commissioner: can assign to all staff except themselves and other commissioners
      if (isCommissioner) {
        return u.role?.name?.toLowerCase() !== 'commissioner';
      }
      // Assistant Commissioner: can assign to all staff except themselves and commissioners
      if (isAssistantCommissioner) {
        return u.role?.name?.toLowerCase() !== 'commissioner' && u.id !== currentUser.id;
      }
      // Unit Head: can only assign staff in their own unit, excluding themselves and other unit heads
      if (isUnitHead) {
        const isInSameUnit = u.department_unit?.id === currentUser.department_unit?.id;
        const isNotUnitHead = !u.designation?.toLowerCase().includes('head') && 
                             !(u.designation?.match(/^[A-Z]{2,3}\d+\/PAP$/) && u.designation?.toLowerCase().includes('1'));
        return isInSameUnit && isNotUnitHead && u.id !== currentUser.id;
      }
      // For regular users, only show users from their unit, excluding themselves
      const isInSameUnit = u.department_unit?.id === currentUser.department_unit?.id;
      return isInSameUnit && u.id !== currentUser.id;
    });
  };

  const handleCreate = async (values: any) => {
    console.log('Create Action Log form values:', values);
    try {
      if (!user) {
        message.error('User not found');
        return;
      }

      // Format the date to ISO string
      const formattedDueDate = values.due_date ? values.due_date.toISOString() : null;

      // Format assigned_to to be an empty array if undefined
      const assignedTo = values.assigned_to || [];

      // For commissioners and assistant commissioners, get the department and unit from the first assigned user
      let departmentId = user.department;
      let departmentUnitId = user.department_unit?.id;

      if ((user.role?.name?.toLowerCase() === 'commissioner' || 
           user.role?.name?.toLowerCase() === 'assistant_commissioner') && 
          assignedTo.length > 0) {
        const firstAssignedUser = users.find(u => u.id.toString() === assignedTo[0]);
        if (firstAssignedUser) {
          departmentId = firstAssignedUser.department;
          departmentUnitId = firstAssignedUser.department_unit?.id;
        }
      }

      const createData: CreateActionLogData = {
        title: values.title,
        description: values.description,
        due_date: formattedDueDate,
        priority: values.priority.charAt(0).toUpperCase() + values.priority.slice(1), // Capitalize first letter
        department_id: departmentId,
        department_unit: departmentUnitId,
        created_by: user.id,
        assigned_to: assignedTo,
        status: 'open'
      };

      // Validate required fields
      if (!createData.title || !createData.description || !createData.priority || !createData.department_id || !createData.department_unit) {
        message.error('Please fill in all required fields');
        return;
      }

      console.log('Creating action log with data:', createData);
      
      const response = await actionLogService.create(createData);
      message.success('Action log created successfully');
      setCreateModalVisible(false);
      createForm.resetFields();
      
      // Update the action logs list with the new data
      setActionLogs(prevLogs => [
        {
          ...response,
          assigned_to: assignedTo,
          status: 'open',
          created_by: user,
          department: { 
            id: departmentId, 
            name: user.department_name,
            code: '',
            description: '',
            units: [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          },
          department_unit: user.department_unit
        } as ActionLog,
        ...prevLogs
      ]);
    } catch (error) {
      console.error('Error creating action log:', error);
      if (error.response?.data) {
        console.error('Server error details:', error.response.data);
        // Handle multiple error fields
        const errorMessages = Object.entries(error.response.data)
          .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages[0] : messages}`)
          .join('\n');
        message.error(`Failed to create action log:\n${errorMessages}`);
      } else {
        message.error('Failed to create action log');
      }
    }
  };

  const handleAssign = async (values: any) => {
    try {
      if (!selectedLog) return;
      
      const assignedToIds = values.assigned_to.map((id: string) => parseInt(id));
      const updateData: ActionLogUpdate = {
        assigned_to: assignedToIds,
        status: 'open'
      };
      
      await actionLogService.update(selectedLog.id, updateData);
      message.success('Action log assigned successfully');
      setAssignModalVisible(false);
      assignForm.resetFields();
      
      // Update the action logs list with the new data
      setActionLogs(prevLogs => 
        prevLogs.map(log => 
          log.id === selectedLog.id 
            ? { 
                ...log,
                assigned_to: assignedToIds,
                status: 'open'
              } as ActionLog
            : log
        )
      );
    } catch (error) {
      console.error('Error assigning action log:', error);
      if (error.response?.data) {
        console.error('Server error details:', error.response.data);
        const errorMessages = Object.entries(error.response.data)
          .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages[0] : messages}`)
          .join('\n');
        message.error(`Failed to assign action log:\n${errorMessages}`);
      } else {
        message.error('Failed to assign action log');
      }
    }
  };

  const handleStatusUpdate = async (values: any) => {
    try {
      if (!selectedLog) return;
      
      // Update the status and add comment
      await actionLogService.update(selectedLog.id, {
        status: values.status as ActionLogStatus,
        comment: values.status_comment
      });
      
      // Fetch the updated log with comments
      const updatedLog = await actionLogService.getById(selectedLog.id);
      
      // Update the action logs list with the new data
      setActionLogs(prevLogs => 
        prevLogs.map(log => 
          log.id === selectedLog.id 
            ? { 
                ...log,
                ...updatedLog,
                status: values.status as ActionLogStatus
              } as ActionLog
            : log
        )
      );
      
      message.success('Status updated successfully');
      setStatusModalVisible(false);
      statusForm.resetFields();
      
      // If comments modal is open, update the comments
      if (commentsModalVisible && selectedLogComments.length > 0) {
        await fetchComments(selectedLog.id);
      }
    } catch (error) {
      console.error('Error updating status:', error);
      message.error('Failed to update status');
    }
  };

  const handleApprove = async (values: any) => {
    try {
      if (!selectedLog) return;
      
      if (!selectedLog.can_approve) {
        message.error('You are not authorized to approve this action log');
        return;
      }
      
      console.log('Approval attempt:', {
        userId: user?.id,
        userName: `${user?.first_name} ${user?.last_name}`,
        designation: user?.designation,
        role: user?.role?.name,
        departmentUnit: user?.department_unit,
        logId: selectedLog.id,
        logUnit: selectedLog.created_by?.department_unit,
        currentApprovalStatus: selectedLog.approval_status,
        currentStatus: selectedLog.status,
        canApprove: selectedLog.can_approve
      });
      
      let approvalStatus: ApprovalStatus = null;
      const isUnitHead = user.designation?.toLowerCase().includes('head');
      const isAssistantCommissioner = user.role?.name?.toLowerCase() === 'assistant_commissioner';
      const isCommissioner = user.role?.name?.toLowerCase() === 'commissioner';
      
      // Check if user is in the same unit as the action log
      const isInSameUnit = selectedLog.created_by?.department_unit?.id === user.department_unit?.id;
      
      console.log('Approval checks:', {
        isUnitHead,
        isAssistantCommissioner,
        isCommissioner,
        isInSameUnit,
        userUnit: user.department_unit?.id,
        logUnit: selectedLog.created_by?.department_unit?.id
      });
      
      if (isUnitHead && isInSameUnit) {
        approvalStatus = 'unit_head_approved';
      } else if (isAssistantCommissioner) {
        approvalStatus = 'assistant_commissioner_approved';
      } else if (isCommissioner) {
        approvalStatus = 'commissioner_approved';
      }
      
      if (!approvalStatus) {
        message.error('You are not authorized to approve this action log');
        return;
      }
      
      await actionLogService.update(selectedLog.id, {
        status: 'closed', // Always close the log when approving
        comment: values.approval_comment,
        approval_status: approvalStatus
      });
      
      message.success('Action log approved successfully');
      setApprovalModalVisible(false);
      approvalForm.resetFields();
      fetchActionLogs();
    } catch (error) {
      console.error('Error approving action log:', error);
      message.error('Failed to approve action log');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
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

  const getFullName = (user: User) => {
    const first = user.first_name?.trim() || '';
    const last = user.last_name?.trim() || '';
    const full = `${first} ${last}`.trim();
    return full || user.username;
  };

  const canAssign = user.role?.can_update_status || false;
  const canUpdateStatus = user.role?.can_update_status || false;
  const canApprove = user.role?.can_approve || false;
  const canConfigure = user.role?.can_configure || false;
  const canCreateLogs = user.role?.can_create_logs || false;
  const canViewAllLogs = user.role?.can_view_all_logs || false;

  // Update status filter options
  const statusFilterOptions = [
    { text: 'Open', value: 'open' },
    { text: 'In Progress', value: 'in_progress' },
    { text: 'Closed', value: 'closed' }
  ];

  const getFilteredLogs = () => {
    let filteredLogs = [...actionLogs];

    // Filter by assigned logs if "Assigned To Me" is selected
    if (showAssignedOnly) {
      filteredLogs = filteredLogs.filter(log => 
        log.assigned_to?.includes(user?.id || 0)
      );
    }

    // Apply search filter
    if (search) {
      const searchLower = search.toLowerCase();
      filteredLogs = filteredLogs.filter(log => 
        log.title.toLowerCase().includes(searchLower) ||
        log.description.toLowerCase().includes(searchLower)
      );
    }

    // Apply status filter
    if (statusFilter) {
      filteredLogs = filteredLogs.filter(log => 
        log.status.toLowerCase() === statusFilter.toLowerCase()
      );
    }

    return filteredLogs;
  };

  const fetchComments = async (logId: number) => {
    try {
      setCommentsLoading(true);
      const response = await actionLogService.getComments(logId);
      
      // Sort comments by date, newest first
      const sortedComments = response.map(comment => ({
        id: comment.id,
        action_log: logId,
        user: {
          id: comment.user.id,
          first_name: comment.user.first_name,
          last_name: comment.user.last_name,
          email: comment.user.email || ''
        },
        comment: comment.comment,
        created_at: comment.created_at,
        updated_at: comment.updated_at,
        status: comment.status,
        is_approved: comment.is_approved,
        replies: comment.replies || []
      }));
      
      setSelectedLogComments(sortedComments);
      
      // Mark comments as read only if they are not from the current user
      const newReadComments = new Set(readComments);
      sortedComments.forEach(comment => {
        if (comment.user.id !== user?.id) {
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

  const handleViewComments = async (log: ActionLog) => {
    try {
      setSelectedLog(log);
      setCommentsLoading(true);
      await fetchComments(log.id);
      setCommentsModalVisible(true);
    } catch (error) {
      console.error('Error fetching comments:', error);
      message.error('Failed to fetch comments');
    } finally {
      setCommentsLoading(false);
    }
  };

  const handleComments = async (log: ActionLog) => {
    setSelectedLog(log);
    setCommentsModalVisible(true);
    setCommentsLoading(true);
    try {
      const comments = await actionLogService.getComments(log.id);
      setSelectedLogComments(comments);
    } catch (error) {
      console.error('Error fetching comments:', error);
      message.error('Failed to fetch comments');
    } finally {
      setCommentsLoading(false);
    }
  };

  const handleAddComment = async () => {
    if (!selectedLog || !newComment.trim()) return;

    setSubmittingComment(true);
    try {
      const comment = await actionLogService.addComment(selectedLog.id, {
        comment: newComment,
        parent_comment_id: replyingTo?.id
      });
      
      if (replyingTo) {
        // Update the parent comment's replies
        setSelectedLogComments(prev => prev.map(c => {
          if (c.id === replyingTo.id) {
            return {
              ...c,
              replies: [...(c.replies || []), comment]
            };
          }
          return c;
        }));
      } else {
        // Add as a new top-level comment
        setSelectedLogComments(prev => [comment, ...prev]);
      }
      
      setNewComment('');
      setReplyingTo(null);
      message.success('Comment added successfully');
    } catch (error) {
      console.error('Error adding comment:', error);
      message.error('Failed to add comment');
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleReply = (comment: LocalActionLogComment) => {
    setReplyingTo({
      id: comment.id,
      comment: comment.comment,
      user: comment.user,
      created_at: comment.created_at,
      updated_at: comment.updated_at,
      status: comment.status ?? 'open',
      is_approved: comment.is_approved ?? false
    });
    setNewComment('');
  };

  const handleCancelReply = () => {
    setReplyingTo(null);
    setNewComment('');
  };

  const getCommentColor = (userId: number) => {
    const colors = [
      '#f0f7ff', // Light blue
      '#f6ffed', // Light green
      '#fff7e6', // Light orange
      '#fff1f0', // Light red
      '#f9f0ff', // Light purple
    ];
    return colors[userId % colors.length];
  };

  const renderComment = (comment: LocalActionLogComment, parent?: LocalActionLogComment, showReplyButton: boolean = false) => {
    const backgroundColor = getCommentColor(comment.user.id);
    return (
      <div style={{
        marginBottom: '16px',
        padding: '12px',
        backgroundColor,
        borderRadius: '8px',
        border: '1px solid #f0f0f0',
        position: 'relative'
      }}>
        {/* If this is a reply, show the parent comment as a quote */}
        {parent && (
          <div style={{
            background: '#f5f5f5',
            borderLeft: '4px solid #1890ff',
            padding: '8px 12px',
            marginBottom: '8px',
            fontStyle: 'italic',
            color: '#555',
            fontSize: '13px',
            borderRadius: '4px'
          }}>
            <span style={{ fontWeight: 500 }}>{parent.user.first_name} {parent.user.last_name}:</span> {parent.comment}
          </div>
        )}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: '8px'
        }}>
          <div style={{ fontWeight: 500 }}>
            {comment.user.first_name} {comment.user.last_name}
          </div>
          <div style={{ color: '#666' }}>
            {format(new Date(comment.created_at), 'MMM dd, yyyy HH:mm')}
          </div>
        </div>
        <div style={{ marginBottom: '8px', whiteSpace: 'pre-wrap' }}>
          {comment.comment}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {/* Show Reply button or label depending on context */}
          {showReplyButton ? (
            <Button
              type="link"
              size="small"
              onClick={() => handleReply(comment)}
              style={{ padding: 0 }}
            >
              Reply
            </Button>
          ) : (
            comment.replies && comment.replies.length > 0 && (
              <span style={{ color: '#1890ff', fontSize: '13px', fontStyle: 'italic' }}>Reply</span>
            )
          )}
          {comment.status && (
            <Tag color={
              comment.status === 'closed' ? 'green' :
              comment.status === 'in_progress' ? 'orange' : 'blue'
            }>
              {comment.status === 'open' ? 'Open' :
                comment.status === 'in_progress' ? 'In Progress' : 'Closed'}
            </Tag>
          )}
          {comment.is_approved && (
            <Tag color="green" icon={<CheckOutlined />}>
              Approved
            </Tag>
          )}
        </div>
        {/* Render replies, passing the current comment as parent */}
        {comment.replies && comment.replies.length > 0 && (
          <div style={{ marginLeft: '24px', marginTop: '12px' }}>
            {comment.replies.map(reply => (
              <div key={reply.id + '-' + comment.id}>
                {renderComment(reply, comment, showReplyButton)}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const handleView = async (log: ActionLog) => {
    setSelectedLog(log);
    setViewModalVisible(true);
    setCommentsLoading(true);
    try {
      const [logDetails, commentsResponse, historyResponse] = await Promise.all([
        actionLogService.getById(log.id),
        actionLogService.getComments(log.id),
        actionLogService.getAssignmentHistory(log.id)
      ]);
      setSelectedLogDetails(logDetails);
      setAssignmentHistory(historyResponse);
      const sortedComments = commentsResponse.map(comment => ({
        id: comment.id,
        action_log: log.id,
        user: {
          id: comment.user.id,
          first_name: comment.user.first_name,
          last_name: comment.user.last_name,
          email: comment.user.email || ''
        },
        comment: comment.comment,
        created_at: comment.created_at,
        updated_at: comment.updated_at,
        status: comment.status,
        is_approved: comment.is_approved,
        replies: comment.replies || []
      }));
      setSelectedLogComments(sortedComments);
    } catch (error) {
      console.error('Error fetching log details:', error);
      message.error('Failed to fetch log details');
    } finally {
      setCommentsLoading(false);
    }
  };

  const renderAssignmentHistory = () => {
    if (!assignmentHistory.length) return null;

    return (
      <div style={{ marginTop: '24px' }}>
        <div style={{ 
          display: 'flex',
          alignItems: 'center',
          marginBottom: '16px'
        }}>
          <HistoryOutlined style={{ color: '#1890ff', fontSize: '16px', marginRight: '12px' }} />
          <h3 style={{ 
            margin: 0,
            fontSize: '16px',
            fontWeight: 600,
            color: '#1a1a1a'
          }}>
            Assignment History
          </h3>
        </div>
        <Timeline style={{ paddingLeft: '28px' }}>
          {assignmentHistory.map((history, idx) => (
            <Timeline.Item key={history.id} color={idx === 0 ? 'green' : idx === assignmentHistory.length - 1 ? 'blue' : 'gray'}>
              <div style={{ marginBottom: '8px' }}>
                <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                  {idx === 0 && <span style={{ color: 'green', fontWeight: 700, marginRight: 8 }}>[Start of Assignment]</span>}
                  {idx === assignmentHistory.length - 1 && <span style={{ color: '#1890ff', fontWeight: 700, marginRight: 8 }}>[Current Assignment]</span>}
                  Assigned by <b>{history.assigned_by.first_name} {history.assigned_by.last_name}</b> to{' '}
                  <span>
                    {history.assigned_to.map((user, i) => (
                      <span key={user.id + '-' + i}>
                        <b>{user.first_name} {user.last_name}</b>{i < history.assigned_to.length - 1 ? ', ' : ''}
                      </span>
                    ))}
                  </span>
                  {' '}on {format(new Date(history.assigned_at), 'MMM dd, yyyy HH:mm')}
                </div>
                {history.comment && (
                  <div style={{ 
                    color: '#666',
                    fontSize: '13px',
                    backgroundColor: '#f5f5f5',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    marginTop: '8px'
                  }}>
                    {history.comment}
                  </div>
                )}
              </div>
            </Timeline.Item>
          ))}
        </Timeline>
      </div>
    );
  };

  const renderViewModal = () => {
    if (!selectedLogDetails) return null;

    return (
      <Modal
        title="View Action Log"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        width={1200}
        footer={null}
      >
        <div style={{ display: 'flex', gap: '32px', maxHeight: '70vh', overflow: 'hidden' }}>
          {/* Left Column */}
          <div style={{ flex: '1.2', minWidth: 0, overflow: 'auto' }}>
            {/* Basic Info Section */}
            <div style={{ 
              marginBottom: '24px',
              padding: '24px',
              backgroundColor: '#fff',
              borderRadius: '8px',
              border: '1px solid #f0f0f0'
            }}>
              <div style={{ 
                display: 'flex',
                alignItems: 'center',
                marginBottom: '16px'
              }}>
                <InfoCircleOutlined style={{ color: '#1890ff', fontSize: '16px', marginRight: '12px' }} />
                <h3 style={{ 
                  margin: 0,
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#1a1a1a'
                }}>
                  Basic Information
                </h3>
              </div>
              <Descriptions column={1}>
                <Descriptions.Item label="Title">{selectedLogDetails.title}</Descriptions.Item>
                <Descriptions.Item label="Description">{selectedLogDetails.description}</Descriptions.Item>
                <Descriptions.Item label="Department">{selectedLogDetails.department?.name}</Descriptions.Item>
                <Descriptions.Item label="Status">
                  <Tag color={getStatusColor(selectedLogDetails.status)}>
                    {selectedLogDetails.status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Priority">
                  <Tag color={selectedLogDetails.priority === 'High' ? 'red' : selectedLogDetails.priority === 'Medium' ? 'orange' : 'green'}>
                    {selectedLogDetails.priority}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Due Date">
                  {selectedLogDetails.due_date ? format(new Date(selectedLogDetails.due_date), 'MMM dd, yyyy HH:mm') : 'Not set'}
                </Descriptions.Item>
                <Descriptions.Item label="Created By">
                  {selectedLogDetails.created_by?.first_name} {selectedLogDetails.created_by?.last_name}
                </Descriptions.Item>
                <Descriptions.Item label="Created At">
                  {format(new Date(selectedLogDetails.created_at), 'MMM dd, yyyy HH:mm')}
                </Descriptions.Item>
              </Descriptions>
            </div>

            {/* Assignment Section */}
            <div style={{ 
              marginBottom: '24px',
              padding: '24px',
              backgroundColor: '#fff',
              borderRadius: '8px',
              border: '1px solid #f0f0f0'
            }}>
              <div style={{ 
                display: 'flex',
                alignItems: 'center',
                marginBottom: '16px'
              }}>
                <UserAddOutlined style={{ color: '#1890ff', fontSize: '16px', marginRight: '12px' }} />
                <h3 style={{ 
                  margin: 0,
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#1a1a1a'
                }}>
                  Assigned To
                </h3>
              </div>
              <Space size={[8, 8]} wrap style={{ paddingLeft: '28px' }}>
                {selectedLogDetails.assigned_to?.map(userId => {
                  const user = users.find(u => u.id === userId);
                  return user ? (
                    <Tag key={user.id}>
                      {user.first_name} {user.last_name}
                    </Tag>
                  ) : null;
                })}
              </Space>

              {/* Assignment History Timeline */}
              {assignmentHistory.length > 0 && (
                <div style={{ marginTop: '24px' }}>
                  <div style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    marginBottom: '16px'
                  }}>
                    <HistoryOutlined style={{ color: '#1890ff', fontSize: '16px', marginRight: '12px' }} />
                    <h3 style={{ 
                      margin: 0,
                      fontSize: '16px',
                      fontWeight: 600,
                      color: '#1a1a1a'
                    }}>
                      Assignment History
                    </h3>
                  </div>
                  <Timeline style={{ paddingLeft: '28px' }}>
                    {assignmentHistory.map((history, idx) => (
                      <Timeline.Item key={history.id} color={idx === 0 ? 'green' : idx === assignmentHistory.length - 1 ? 'blue' : 'gray'}>
                        <div style={{ marginBottom: '8px' }}>
                          <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                            {idx === 0 && <span style={{ color: 'green', fontWeight: 700, marginRight: 8 }}>[Start of Assignment]</span>}
                            {idx === assignmentHistory.length - 1 && <span style={{ color: '#1890ff', fontWeight: 700, marginRight: 8 }}>[Current Assignment]</span>}
                            Assigned by <b>{history.assigned_by.first_name} {history.assigned_by.last_name}</b> to{' '}
                            <span>
                              {history.assigned_to.map((user, i) => (
                                <span key={user.id + '-' + i}>
                                  <b>{user.first_name} {user.last_name}</b>{i < history.assigned_to.length - 1 ? ', ' : ''}
                                </span>
                              ))}
                            </span>
                            {' '}on {format(new Date(history.assigned_at), 'MMM dd, yyyy HH:mm')}
                          </div>
                          {history.comment && (
                            <div style={{ 
                              color: '#666',
                              fontSize: '13px',
                              backgroundColor: '#f5f5f5',
                              padding: '8px 12px',
                              borderRadius: '4px',
                              marginTop: '8px'
                            }}>
                              {history.comment}
                            </div>
                          )}
                        </div>
                      </Timeline.Item>
                    ))}
                  </Timeline>
                </div>
              )}
            </div>

            {/* Attachments Section */}
            <div style={{ 
              marginBottom: '24px',
              padding: '24px',
              backgroundColor: '#fff',
              borderRadius: '8px',
              border: '1px solid #f0f0f0'
            }}>
              <div style={{ 
                display: 'flex',
                alignItems: 'center',
                marginBottom: '16px'
              }}>
                <PaperClipOutlined style={{ color: '#1890ff', fontSize: '16px', marginRight: '12px' }} />
                <h3 style={{ 
                  margin: 0,
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#1a1a1a'
                }}>
                  Attachments
                </h3>
              </div>
              <List
                dataSource={selectedLogDetails.attachments || []}
                renderItem={attachment => (
                  <List.Item>
                    <a href={attachment.file} target="_blank" rel="noopener noreferrer">
                      {attachment.filename}
                    </a>
                  </List.Item>
                )}
              />
            </div>
          </div>

          {/* Right Column - Comments */}
          <div style={{ 
            flex: '0.8',
            minWidth: 0,
            maxHeight: '70vh',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#fff',
            borderRadius: '8px',
            border: '1px solid #f0f0f0',
            padding: '24px',
          }}>
            <div style={{ 
              display: 'flex',
              alignItems: 'center',
              marginBottom: '16px'
            }}>
              <CommentOutlined style={{ color: '#1890ff', fontSize: '16px', marginRight: '12px' }} />
              <h3 style={{ 
                margin: 0,
                fontSize: '16px',
                fontWeight: 600,
                color: '#1a1a1a'
              }}>
                Comments
              </h3>
            </div>
            {commentsLoading ? (
              <div style={{ textAlign: 'center', padding: '20px' }}>
                <Spin />
              </div>
            ) : (
              <div style={{ 
                flex: 1,
                overflowY: 'auto',
                maxHeight: 'calc(70vh - 80px)',
                paddingRight: '8px'
              }}>
                {selectedLogComments.map(comment => (
                  <div key={comment.id} style={{ marginBottom: '16px' }}>
                    {renderComment(comment, undefined, false)}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Modal>
    );
  };

  const columns: ColumnsType<ActionLog> = [
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      width: '25%',
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
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: '10%',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}
        </Tag>
      ),
      filters: [
        { text: 'Open', value: 'open' },
        { text: 'In Progress', value: 'in_progress' },
        { text: 'Closed', value: 'closed' }
      ],
      onFilter: (value: any, record: ActionLog) => record.status.toLowerCase() === String(value).toLowerCase(),
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
      width: '10%',
      render: (priority: string) => (
        <Tag color={priority === 'High' ? 'red' : priority === 'Medium' ? 'orange' : 'green'}>
          {priority}
        </Tag>
      ),
    },
    {
      title: 'Assigned To',
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      width: '15%',
      render: (assigned: number[] | null) => {
        if (!assigned || assigned.length === 0) {
          return <span style={{ color: '#999' }}>Unassigned</span>;
        }
        
        const assignedUsers = users.filter(user => assigned.includes(user.id));
        if (assignedUsers.length === 0) {
          return <span style={{ color: '#999' }}>Unassigned</span>;
        }

        // If current user is assigned, show "Me" first
        const currentUserId = user?.id || 0;
        const isCurrentUserAssigned = assigned.includes(currentUserId);
        
        if (isCurrentUserAssigned) {
          const otherUsers = assignedUsers.filter(u => u.id !== currentUserId);
          if (otherUsers.length === 0) {
            return (
              <Tag color="default" style={{ margin: 0 }}>
                Me
              </Tag>
            );
          }
          return (
            <Space size={[4, 4]} wrap>
              <Tag color="default">Me</Tag>
              {otherUsers.map(u => (
                <Tag key={u.id} color="default">
                  {u.first_name} {u.last_name}
                </Tag>
              ))}
            </Space>
          );
        }
        
        return (
          <Space size={[4, 4]} wrap>
            {assignedUsers.map(u => (
              <Tag key={u.id} color="default">
                {u.first_name} {u.last_name}
              </Tag>
            ))}
          </Space>
        );
      }
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: '15%',
      render: (date: string) => format(new Date(date), 'yyyy-MM-dd'),
    },
    {
      title: 'Due Date',
      dataIndex: 'due_date',
      key: 'due_date',
      width: '15%',
      render: (date: string, record: ActionLog) => {
        if (!date) return '-';
        
        const dueDate = new Date(date);
        const today = new Date();
        // Set both dates to start of day to get accurate day difference
        const startOfDueDate = new Date(dueDate.getFullYear(), dueDate.getMonth(), dueDate.getDate());
        const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        const daysRemaining = Math.ceil((startOfDueDate.getTime() - startOfToday.getTime()) / (1000 * 60 * 60 * 24));
        
        return (
          <div>
            <div>{format(dueDate, 'yyyy-MM-dd')}</div>
            <div style={{ marginTop: '4px' }}>
              <Tag color={daysRemaining <= 5 ? 'red' : 'green'}>
                {daysRemaining < 0 ? (
                  'Overdue'
                ) : daysRemaining === 0 ? (
                  '0 days remaining'
                ) : (
                  `${daysRemaining} days remaining`
                )}
              </Tag>
            </div>
          </div>
        );
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: '10%',
      render: (text: string, record: ActionLog) => {
        // Update unit head detection to check for specific designation pattern
        const isUnitHead = user.designation?.toLowerCase().includes('head') || 
                          (user.designation?.match(/^[A-Z]{2,3}\d+\/PAP$/) && user.designation?.toLowerCase().includes('1'));
        const isCommissioner = user.role?.name?.toLowerCase() === 'commissioner';
        const isAssistantCommissioner = user.role?.name?.toLowerCase() === 'assistant_commissioner';
        const userUnitId = user.department_unit?.id;
        const isInSameUnit = record.created_by?.department_unit?.id === user.department_unit?.id;
        
        // Update canAssign logic to be similar to assistant commissioner
        const canAssign = isUnitHead || isCommissioner || isAssistantCommissioner;
        
        console.log('Action log assignment check:', {
          logId: record.id,
          isUnitHead,
          isCommissioner,
          isAssistantCommissioner,
          userUnitId,
          recordUnitId: record.created_by?.department_unit?.id,
          isInSameUnit,
          canAssign,
          userDesignation: user.designation,
          assignedTo: record.assigned_to
        });

        const isAssignedToMe = record.assigned_to?.includes(user?.id || 0);
        const isAssigned = record.assigned_to && record.assigned_to.length > 0;
        const isClosed = record.status === 'closed';

        // Calculate days remaining for reassignment
        const dueDate = record.due_date ? new Date(record.due_date) : null;
        const today = new Date();
        const startOfDueDate = new Date(dueDate?.getFullYear() || 0, dueDate?.getMonth() || 0, dueDate?.getDate() || 0);
        const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        const daysRemaining = dueDate ? Math.ceil((startOfDueDate.getTime() - startOfToday.getTime()) / (1000 * 60 * 60 * 24)) : null;
        const canReassign = isAssigned && daysRemaining === 0;
        
        // Get assignable users
        const assignableUsers = getFilteredUsers(user);
        
        // Determine if user can approve based on role, designation, current approval status, and API flag
        const canApprove = record.can_approve && (
          // Unit Head can approve if they are in the same unit and no approval yet
          (isUnitHead && !record.approval_status && isInSameUnit) ||
          // Assistant Commissioner can approve after Unit Head
          (isAssistantCommissioner && record.approval_status === 'unit_head_approved') ||
          // Commissioner can approve after Assistant Commissioner
          (isCommissioner && record.approval_status === 'assistant_commissioner_approved')
        );

        return (
          <Space>
            <Button 
              type="link" 
              onClick={() => handleView(record)}
            >
              View
            </Button>
            {canAssign && (
              isAssigned ? (
                canReassign ? (
                  <Button 
                    type="link" 
                    onClick={() => {
                      setSelectedLog(record);
                      setAssignModalVisible(true);
                    }}
                  >
                    Re-assign
                  </Button>
                ) : (
                  <Button 
                    type="link" 
                    disabled
                    style={{ color: '#999', cursor: 'not-allowed' }}
                  >
                    Re-assign
                  </Button>
                )
              ) : (
                <Button 
                  type="link" 
                  onClick={() => {
                    setSelectedLog(record);
                    setAssignModalVisible(true);
                  }}
                >
                  {assignableUsers.length > 0 ? 'Assign' : 'No Users Available'}
                </Button>
              )
            )}
            {isAssignedToMe && (
              <Button
                type="link"
                onClick={() => {
                  setSelectedLog(record);
                  setStatusModalVisible(true);
                }}
              >
                Update Status
              </Button>
            )}
            {canApprove && (
              <Button
                type="link"
                onClick={() => {
                  setSelectedLog(record);
                  setApprovalModalVisible(true);
                }}
              >
                Approve
              </Button>
            )}
            <Button
              type="link"
              onClick={() => handleViewComments(record)}
            >
              Comments
            </Button>
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
    } else if (e.key === 'assignedToMe') {
      setShowAssignedOnly(true);
    } else if (e.key === 'actionLogs') {
      setShowAssignedOnly(false);
    } else if (e.key === 'logout') {
      handleLogout();
    }
  };

  const renderUserOptions = () => {
    if (!user) return [];
    const filteredUsers = getFilteredUsers(user);
    return filteredUsers.map(user => ({
      label: `${user.first_name} ${user.last_name}`,
      value: user.id.toString(),
      key: `user-${user.id}`
    }));
  };

  const menuItems = [
    {
      key: 'actionLogs',
      icon: <FileTextOutlined />,
      label: (typeof user.role === 'string' ? user.role : user.role?.name)?.toLowerCase().includes('commissioner')
        ? 'All Action Logs'
        : 'All Action Logs',
    },
    {
      key: 'assignedToMe',
      icon: <UserOutlined />,
      label: 'Assigned To Me',
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

  const handleFileUpload = async (values: any) => {
    try {
      if (!user) {
        message.error('User not found');
        return;
      }

      const file = values.file?.fileList?.[0]?.originFileObj;
      if (!file) {
        message.error('Please select a file to upload');
        return;
      }

      // Read the file
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const data = e.target?.result;
          let rows: string[][] = [];

          // Check file type and parse accordingly
          if (file.name.endsWith('.csv')) {
            // Handle CSV
            const text = data as string;
            rows = text.split('\n')
              .map(row => row.trim())
              .filter(row => row.length > 0)
              .map(row => row.split(',').map(cell => cell.trim()));
          } else {
            // Handle Excel
            const workbook = XLSX.read(data, { type: 'binary' });
            const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
            rows = XLSX.utils.sheet_to_json(firstSheet, { header: 1 }) as string[][];
          }

          if (rows.length < 2) {
            message.error('File must contain at least a header row and one data row');
            return;
          }

          // Get headers from first row and convert to lowercase for case-insensitive comparison
          const headers = rows[0].map(h => h.toString().trim().toLowerCase());
          
          // Validate required headers
          const requiredHeaders = ['title', 'description'];
          const missingHeaders = requiredHeaders.filter(h => !headers.includes(h));
          if (missingHeaders.length > 0) {
            message.error(`Missing required headers: ${missingHeaders.join(', ')}`);
            return;
          }

          // Process rows and create action logs
          const actionLogs = rows.slice(1).map(row => {
            const assignedToStr = row[headers.indexOf('assigned_to')] || '';
            const assignedTo = assignedToStr.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));
            
            return {
              title: row[headers.indexOf('title')],
              description: row[headers.indexOf('description')],
              due_date: row[headers.indexOf('due_date')] || null,
              priority: (row[headers.indexOf('priority')] || 'Medium').toUpperCase(),
              department_id: user.department,
              department_unit: user.department_unit?.id,
              created_by: user.id,
              assigned_to: assignedTo,
              status: 'open' as ActionLogStatus
            } as CreateActionLogData;
          });

          // Create action logs in the backend
          const createdLogs = await Promise.all(actionLogs.map(log => actionLogService.create(log)));

          message.success('Action logs created successfully');
          setCreateModalVisible(false);
          createForm.resetFields();
          
          // Update the action logs list with the new data
          setActionLogs(prevLogs => [...createdLogs, ...prevLogs]);
        } catch (error) {
          console.error('Error processing file:', error);
          message.error('Failed to process file');
        }
      };
      reader.readAsBinaryString(file);
    } catch (error) {
      console.error('Error uploading file:', error);
      message.error('Failed to upload file');
    }
  };

  // Add these effects after the form instances
  useEffect(() => {
    if (createModalVisible) {
      createForm.resetFields();
    }
  }, [createModalVisible, createForm]);
  useEffect(() => {
    if (assignModalVisible) {
      assignForm.resetFields();
    }
  }, [assignModalVisible, assignForm]);

  const renderStaffOption = (staff: User) => (
    <Select.Option key={staff.id} value={staff.id}>
      {staff.first_name} {staff.last_name} ({staff.designation?.name || 'No Designation'})
    </Select.Option>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={200} style={{ background: '#fff', borderRight: '1px solid #e0e0e0', position: 'fixed', height: '100vh', left: 0, top: 0, zIndex: 10 }}>
        {/* User Profile Section */}
        <div
          style={{
            height: 140,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px 0',
            borderBottom: '1px solid #f0f0f0',
            background: '#fff',
            marginBottom: 16,
          }}
        >
          <Avatar
            size={80}
            icon={<UserOutlined />}
            style={{
              fontSize: 32,
              marginBottom: 8,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: '#ffffff',
              border: '3px solid rgba(255, 255, 255, 0.2)',
              boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3), 0 2px 8px rgba(0, 0, 0, 0.1)',
              backdropFilter: 'blur(10px)',
              borderRadius: '50%',
              transition: 'all 0.3s ease',
              cursor: 'pointer',
              flexShrink: 0
            }}
          />
          <div style={{ fontWeight: 600, fontSize: 16, color: '#222', textAlign: 'center', lineHeight: 1, marginBottom: 6 }}>{user ? `${user.first_name} ${user.last_name}` : ''}</div>
          <div style={{ fontSize: 13, color: '#888', textAlign: 'center', lineHeight: 1 }}>{user?.designation || ''}</div>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedMenuKey]}
          style={{ height: '100%', borderRight: 0 }}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout style={{ marginLeft: 200, minHeight: '100vh' }}>
        <Content style={{ padding: 24, minHeight: 280, background: '#fff' }}>
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0, marginBottom: 24 }}>Action Logs</h1>
            <div style={{ marginBottom: 16, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Input.Search
                placeholder="Search action logs..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ width: 240 }}
                allowClear
              />
              <Select
                placeholder="Filter by status"
                value={statusFilter || undefined}
                onChange={value => setStatusFilter(value)}
                allowClear
                style={{ width: 180 }}
                options={statusFilterOptions}
              />
              <Button
                type={showAssignedOnly ? 'primary' : 'default'}
                icon={<UserOutlined />}
                onClick={() => setShowAssignedOnly(v => !v)}
              >
                Assigned To Me
              </Button>
              {canCreateLogs && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setCreateModalVisible(true)}
                >
                  Create Action Log
                </Button>
              )}
            </div>
            <Table
              columns={columns}
              dataSource={getFilteredLogs()}
              loading={loading}
              rowKey="id"
              pagination={{ pageSize: 10 }}
              bordered
              style={{ background: '#fff', borderRadius: 8 }}
            />
            {/* Modals and dialogs */}
            {renderViewModal()}
            <Modal
              title="Create Action Log"
              open={createModalVisible}
              onCancel={() => setCreateModalVisible(false)}
              footer={null}
              destroyOnHidden
            >
              <Form
                form={createForm}
                layout="vertical"
                onFinish={handleCreate}
              >
                <Form.Item name="title" label="Title" rules={[{ required: true, message: 'Please enter a title' }]}><Input /></Form.Item>
                <Form.Item name="description" label="Description" rules={[{ required: true, message: 'Please enter a description' }]}><Input.TextArea rows={3} /></Form.Item>
                <Form.Item name="due_date" label="Due Date"><DatePicker style={{ width: '100%' }} /></Form.Item>
                <Form.Item name="priority" label="Priority" rules={[{ required: true, message: 'Please select a priority' }]}><Select options={[{ value: 'High' }, { value: 'Medium' }, { value: 'Low' }]} /></Form.Item>
                <Form.Item name="assigned_to" label="Assign To"><Select mode="multiple" options={renderUserOptions()} /></Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit">Create</Button>
                </Form.Item>
              </Form>
            </Modal>
            <Modal
              title="Assign Action Log"
              open={assignModalVisible}
              onCancel={() => setAssignModalVisible(false)}
              footer={null}
              destroyOnHidden
            >
              <Form form={assignForm} layout="vertical" onFinish={handleAssign}>
                <Form.Item name="assigned_to" label="Assign To" rules={[{ required: true, message: 'Please select at least one user' }]}><Select mode="multiple" options={renderUserOptions()} /></Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit">Assign</Button>
                </Form.Item>
              </Form>
            </Modal>
            <Modal
              title="Update Status"
              open={statusModalVisible}
              onCancel={() => setStatusModalVisible(false)}
              footer={null}
              destroyOnHidden
            >
              <Form
                form={statusForm}
                onFinish={handleStatusUpdate}
                layout="vertical"
              >
                <Form.Item
                  name="status"
                  label="Status"
                  rules={[{ required: true, message: 'Please select a status' }]}
                >
                  <Select>
                    <Select.Option value="open">Open</Select.Option>
                    <Select.Option value="in_progress">In Progress</Select.Option>
                    <Select.Option value="closed">Closed</Select.Option>
                  </Select>
                </Form.Item>

                <Form.Item
                  name="status_comment"
                  label="Comment"
                  rules={[{ required: true, message: 'Please enter a comment' }]}
                >
                  <Input.TextArea rows={4} />
                </Form.Item>

                <Form.Item>
                  <Button type="primary" htmlType="submit">
                    Update Status
                  </Button>
                </Form.Item>
              </Form>
            </Modal>
            <Modal
              title="Approve Action Log"
              open={approvalModalVisible}
              onCancel={() => setApprovalModalVisible(false)}
              footer={null}
              destroyOnHidden
            >
              <Form form={approvalForm} layout="vertical" onFinish={handleApprove}>
                <Form.Item name="approval_comment" label="Approval Comment"> <Input.TextArea rows={3} /> </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit">Approve</Button>
                </Form.Item>
              </Form>
            </Modal>
            <Modal
              title="Comments"
              open={commentsModalVisible}
              onCancel={() => setCommentsModalVisible(false)}
              footer={null}
              width={700}
              destroyOnHidden
            >
              <Spin spinning={commentsLoading}>
                <div style={{ maxHeight: 400, overflowY: 'auto', marginBottom: 16 }}>
                  {selectedLogComments.map(comment => (
                    <div key={comment.id} style={{ marginBottom: '16px' }}>
                      {renderComment(comment, undefined, true)}
                    </div>
                  ))}
                </div>
                {replyingTo && (
                  <div style={{ marginBottom: 8, background: '#f0f7ff', padding: 8, borderRadius: 4 }}>
                    Replying to: <strong>{replyingTo.user.first_name} {replyingTo.user.last_name}</strong>
                    <Button type="link" size="small" onClick={handleCancelReply} style={{ marginLeft: 8 }}>Cancel</Button>
                  </div>
                )}
                <Input.TextArea
                  value={newComment}
                  onChange={e => setNewComment(e.target.value)}
                  rows={2}
                  placeholder="Add a comment..."
                  style={{ marginBottom: 8 }}
                />
                <Button
                  type="primary"
                  onClick={handleAddComment}
                  loading={submittingComment}
                  disabled={!newComment.trim()}
                >
                  Add Comment
                </Button>
              </Spin>
            </Modal>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default EconomistDashboard;