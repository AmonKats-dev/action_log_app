import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../auth/AuthContext';
import { actionLogService } from '../../../services/actionLogService';
import { departmentService } from '../../../services/departmentService';
import { userService } from '../../../services/userService';
import { ActionLog, ActionLogStatus, ActionLogUpdate } from '../../../types/actionLog';
import { Department, DepartmentUnit } from '../../../types/department';
import { Button, Card, Table, Modal, Form, Input, message, Space, Tag, Select, DatePicker, Layout, Menu, Avatar, Tooltip, Timeline, Spin, Badge } from 'antd';
import { PlusOutlined, CheckOutlined, FilterOutlined, UserAddOutlined, UserOutlined, FileTextOutlined, FormOutlined, TeamOutlined, SettingOutlined } from '@ant-design/icons';
import { format } from 'date-fns';
import { Navigate, useNavigate } from 'react-router-dom';
import { User } from '../../../types/user';
import { Dayjs } from 'dayjs';
import UserDisplay from '../../../components/UserDisplay';

const { Sider, Content } = Layout;

const AssistantDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [actionLogs, setActionLogs] = useState<ActionLog[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [departmentUnits, setDepartmentUnits] = useState<DepartmentUnit[]>([]);
  const [loading, setLoading] = useState(true);
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
  const [statusModalVisible, setStatusModalVisible] = useState(false);
  const [statusForm] = Form.useForm();
  const [commentsModalVisible, setCommentsModalVisible] = useState(false);
  const [selectedLogComments, setSelectedLogComments] = useState<any[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);

  useEffect(() => {
    const initializeData = async () => {
      if (!user) {
        navigate('/login');
        return;
      }

      try {
        await Promise.all([
          fetchDepartments(),
          fetchDepartmentUnits(),
          fetchActionLogs(),
          fetchUsers()
        ]);
      } catch (error) {
        console.error('Error initializing data:', error);
        message.error('Failed to initialize dashboard data');
      }
    };
    initializeData();
  }, [user]);

  const fetchActionLogs = async () => {
    try {
      const response = await actionLogService.getAll();
      const logs = response.results || response;
      const logsArray = Array.isArray(logs) ? logs : [];
      setActionLogs(logsArray);
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
      let departmentsData: Department[] = [];
      
      if (Array.isArray(response)) {
        departmentsData = response;
      } else if (response && typeof response === 'object') {
        interface PaginatedResponse {
          results?: Department[];
        }
        const typedResponse = response as PaginatedResponse;
        departmentsData = Array.isArray(typedResponse.results) ? typedResponse.results : [];
      }
      
      setDepartments(departmentsData);
    } catch (error) {
      console.error('Error fetching departments:', error);
      message.error('Failed to fetch departments');
      setDepartments([]);
    }
  };

  const fetchDepartmentUnits = async () => {
    try {
      const response = await departmentService.getUnits();
      let units: DepartmentUnit[] = [];
      
      if (Array.isArray(response)) {
        units = response;
      } else if (response && typeof response === 'object') {
        // Handle paginated response
        interface PaginatedResponse {
          count: number;
          next: string | null;
          previous: string | null;
          results: DepartmentUnit[];
        }
        const typedResponse = response as unknown as PaginatedResponse;
        if (Array.isArray(typedResponse.results)) {
          units = typedResponse.results;
        } else {
          console.warn('Unexpected response format:', response);
          units = [];
        }
      }
      
      setDepartmentUnits(units);
    } catch (error) {
      console.error('Error fetching department units:', error);
      message.error('Failed to fetch department units');
      setDepartmentUnits([]);
    }
  };

  const fetchUsers = async () => {
    if (!user) return;

    try {
      setUsersLoading(true);
      // If user is a department unit head, only fetch users from their unit
      if (user.department_unit) {
        const data = await userService.getByDepartmentUnit(user.department_unit.id);
        const usersArray = Array.isArray(data) ? data.filter(u => u.is_active && u.id !== user.id) : [];
        setUsers(usersArray);
      } else {
        const data = await userService.getByDepartment(user.department);
        const usersArray = Array.isArray(data) ? data.filter(u => u.is_active && u.id !== user.id) : [];
        setUsers(usersArray);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
      message.error('Failed to fetch users');
    } finally {
      setUsersLoading(false);
    }
  };

  const handleCreate = async (values: any) => {
    try {
      await actionLogService.create({
        ...values,
        created_by: user.id,
        department: user.department
      });
      message.success('Action log created successfully');
      setCreateModalVisible(false);
      form.resetFields();
      fetchActionLogs();
    } catch (error) {
      console.error('Error creating action log:', error);
      message.error('Failed to create action log');
    }
  };

  const handleAssign = async (values: any) => {
    try {
      if (!selectedLog) return;
      
      const assignedToIds = values.assigned_to.map((id: string) => parseInt(id));
      const updateData: ActionLogUpdate = {
        assigned_to: assignedToIds
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
                assigned_to: assignedToIds
              }
            : log
        )
      );
    } catch (error) {
      console.error('Error assigning action log:', error);
      message.error('Failed to assign action log');
    }
  };

  const handleStatusUpdate = async (values: any) => {
    try {
      if (!selectedLog) return;
      
      await actionLogService.update(selectedLog.id, {
        status: values.status,
        comment: values.status_comment
      });
      message.success('Status updated successfully');
      setStatusModalVisible(false);
      statusForm.resetFields();
      fetchActionLogs();
    } catch (error) {
      console.error('Error updating status:', error);
      message.error('Failed to update status');
    }
  };

  const handleApprove = async (logId: number) => {
    try {
      await actionLogService.approve(logId);
      message.success('Action log approved successfully');
      fetchActionLogs();
    } catch (error) {
      console.error('Error approving action log:', error);
      message.error('Failed to approve action log');
    }
  };

  const handleReject = async (logId: number, reason: string) => {
    try {
      await actionLogService.reject(logId, { reason });
      message.success('Action log rejected successfully');
      fetchActionLogs();
    } catch (error) {
      console.error('Error rejecting action log:', error);
      message.error('Failed to reject action log');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleMenuClick = (e: any) => {
    setSelectedMenuKey(e.key);
  };

  const fetchComments = async (logId: number) => {
    try {
      setCommentsLoading(true);
      const response = await actionLogService.getComments(logId);
      setSelectedLogComments(response);
    } catch (error) {
      console.error('Error fetching comments:', error);
      message.error('Failed to fetch comments');
    } finally {
      setCommentsLoading(false);
    }
  };

  const handleViewComments = async (logId: number) => {
    await fetchComments(logId);
    setCommentsModalVisible(true);
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) {
      message.warning('Please enter a comment');
      return;
    }

    try {
      setSubmittingComment(true);
      await actionLogService.addComment(selectedLogComments[0]?.action_log, {
        content: newComment,
        user: user.id
      });
      message.success('Comment added successfully');
      setNewComment('');
      await fetchComments(selectedLogComments[0]?.action_log);
    } catch (error) {
      console.error('Error adding comment:', error);
      message.error('Failed to add comment');
    } finally {
      setSubmittingComment(false);
    }
  };

  const columns = [
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
        <Tag color={status === 'open' ? 'green' : status === 'in_progress' ? 'blue' : 'red'}>
          {status.toUpperCase()}
        </Tag>
      ),
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
        
        return assignedUsers.map(user => 
          `${user.first_name} ${user.last_name}`
        ).join(', ');
      }
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: '15%',
      render: (date: string) => format(new Date(date), 'yyyy-MM-dd HH:mm'),
    },
    {
      title: 'Due Date',
      dataIndex: 'due_date',
      key: 'due_date',
      width: '15%',
      render: (date: string) => date ? format(new Date(date), 'yyyy-MM-dd HH:mm') : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: '10%',
      render: (text: string, record: ActionLog) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/action-logs/${record.id}`)}>
            View
          </Button>
          {user.department_unit && user.department_unit.id === record.department_unit && user.designation?.toLowerCase().includes('head') && (
            <Button 
              type="link" 
              onClick={() => {
                setSelectedLog(record);
                setAssignModalVisible(true);
              }}
            >
              Assign
            </Button>
          )}
          {Array.isArray(record.assigned_to) && record.assigned_to.includes(user.id) && (
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
          <Button
            type="link"
            onClick={() => handleViewComments(record.id)}
          >
            Comments
          </Button>
          {record.status === 'in_progress' && (
            <>
              <Button
                type="link"
                onClick={() => handleApprove(record.id)}
              >
                Approve
              </Button>
              <Button
                type="link"
                danger
                onClick={() => {
                  Modal.confirm({
                    title: 'Reject Action Log',
                    content: (
                      <Form>
                        <Form.Item
                          name="reason"
                          rules={[{ required: true, message: 'Please enter a reason' }]}
                        >
                          <Input.TextArea placeholder="Enter rejection reason" />
                        </Form.Item>
                      </Form>
                    ),
                    onOk: (close) => {
                      const form = Form.useForm()[0];
                      form.validateFields().then(values => {
                        handleReject(record.id, values.reason);
                        close();
                      });
                    },
                  });
                }}
              >
                Reject
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={200} theme="light">
        <UserDisplay 
          user={user} 
          departmentName={departments.find(d => d.id === user.department)?.name}
        />
        <Menu
          mode="inline"
          selectedKeys={[selectedMenuKey]}
          onClick={handleMenuClick}
        >
          <Menu.Item key="actionLogs" icon={<FileTextOutlined />}>
            Action Logs
          </Menu.Item>
          <Menu.Item key="logout" icon={<SettingOutlined />} onClick={handleLogout}>
            Logout
          </Menu.Item>
        </Menu>
      </Sider>
      <Content style={{ padding: '24px' }}>
        <Card title="Assistant Commissioner Dashboard">
          <Space style={{ marginBottom: 16 }}>
            <Input.Search
              placeholder="Search action logs"
              onSearch={value => setSearch(value)}
              style={{ width: 200 }}
            />
            <Select
              style={{ width: 200 }}
              placeholder="Filter by status"
              onChange={value => setStatusFilter(value)}
              options={[
                { label: 'All Statuses', value: '' },
                { label: 'Open', value: 'open' },
                { label: 'In Progress', value: 'in_progress' },
                { label: 'Closed', value: 'closed' },
              ]}
            />
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              Create Action Log
            </Button>
          </Space>

          <Table
            columns={columns}
            dataSource={actionLogs}
            loading={loading}
            rowKey="id"
          />
        </Card>

        <Modal
          title="Create Action Log"
          open={createModalVisible}
          onCancel={() => setCreateModalVisible(false)}
          footer={null}
        >
          <Form form={form} onFinish={handleCreate} layout="vertical">
            <Form.Item
              name="title"
              label="Title"
              rules={[{ required: true, message: 'Please enter a title' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="description"
              label="Description"
              rules={[{ required: true, message: 'Please enter a description' }]}
            >
              <Input.TextArea />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">
                Create
              </Button>
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="Assign Action Log"
          open={assignModalVisible}
          onCancel={() => setAssignModalVisible(false)}
          footer={null}
        >
          <Form form={assignForm} onFinish={handleAssign} layout="vertical">
            <Form.Item
              name="assigned_to"
              label="Assign To"
              rules={[
                { required: true, message: 'Please select at least one user' },
                { type: 'array', min: 1, message: 'Please select at least one user' }
              ]}
            >
              <Select
                mode="multiple"
                loading={usersLoading}
                placeholder="Select users"
                options={users.map(user => ({
                  label: `${user.first_name} ${user.last_name}`,
                  value: user.id.toString()
                }))}
                style={{ minHeight: 80 }}
                allowClear
              />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button onClick={() => setAssignModalVisible(false)}>
                  Cancel
                </Button>
                <Button type="primary" htmlType="submit">
                  Assign
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="Update Status"
          open={statusModalVisible}
          onCancel={() => setStatusModalVisible(false)}
          footer={null}
        >
          <Form form={statusForm} onFinish={handleStatusUpdate} layout="vertical">
            <Form.Item
              name="status"
              label="Status"
              rules={[{ required: true, message: 'Please select a status' }]}
            >
              <Select
                placeholder="Select status"
                options={[
                  { label: 'Open', value: 'open' },
                  { label: 'In Progress', value: 'in_progress' },
                  { label: 'Closed', value: 'closed' },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="status_comment"
              label="Comment"
              rules={[{ required: true, message: 'Please enter a comment' }]}
            >
              <Input.TextArea />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">
                Update
              </Button>
            </Form.Item>
          </Form>
        </Modal>

        <Modal
          title="Comments"
          open={commentsModalVisible}
          onCancel={() => setCommentsModalVisible(false)}
          footer={null}
          width={600}
        >
          <div style={{ maxHeight: '400px', overflowY: 'auto', marginBottom: '16px' }}>
            <Timeline>
              {selectedLogComments.map((comment, index) => (
                <Timeline.Item key={index}>
                  <p><strong>{comment.user?.name}</strong> - {format(new Date(comment.created_at), 'yyyy-MM-dd HH:mm')}</p>
                  <p>{comment.content}</p>
                </Timeline.Item>
              ))}
            </Timeline>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <Input.TextArea
              value={newComment}
              onChange={e => setNewComment(e.target.value)}
              placeholder="Add a comment..."
              rows={3}
            />
            <Button
              type="primary"
              onClick={handleAddComment}
              loading={submittingComment}
            >
              Add Comment
            </Button>
          </div>
        </Modal>
      </Content>
    </Layout>
  );
};

export default AssistantDashboard; 