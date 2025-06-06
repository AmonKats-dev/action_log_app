import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../auth/AuthContext';
import { actionLogService } from '../../../services/actionLogService';
import { departmentService, DepartmentUnit } from '../../../services/departmentService';
import { userService } from '../../../services/userService';
import { ActionLog, ActionLogStatus } from '../../../types/actionLog';
import { Department } from '../../../types/department';
import { Button, Card, Table, Modal, Form, Input, message, Space, Tag, Select, DatePicker, Layout, Menu, Avatar, Tooltip, Timeline, Spin, Badge, Tabs } from 'antd';
import { PlusOutlined, CheckOutlined, FilterOutlined, UserAddOutlined, UserOutlined, FileTextOutlined, FormOutlined, TeamOutlined, SettingOutlined, DashboardOutlined } from '@ant-design/icons';
import { format } from 'date-fns';
import { Navigate, useNavigate } from 'react-router-dom';
import { User } from '../../../types/user';
import { Dayjs } from 'dayjs';
import UserDisplay from '../../../components/UserDisplay';

const { Sider, Content } = Layout;
const { TabPane } = Tabs;

const AdminDashboard: React.FC = () => {
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
  const [selectedMenuKey, setSelectedMenuKey] = useState('dashboard');
  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [statusModalVisible, setStatusModalVisible] = useState(false);
  const [statusForm] = Form.useForm();
  const [commentsModalVisible, setCommentsModalVisible] = useState(false);
  const [selectedLogComments, setSelectedLogComments] = useState<any[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [activeTab, setActiveTab] = useState('actionLogs');
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [rejectForm] = Form.useForm();

  useEffect(() => {
    const initializeData = async () => {
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
  }, []);

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
      const units = await departmentService.getUnits();
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
    }
  };

  const fetchUsers = async () => {
    try {
      setUsersLoading(true);
      const data = await userService.getAll();
      const usersArray = Array.isArray(data) ? data.filter(user => user.is_active) : [];
      setUsers(usersArray);
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

  const handleStatusUpdate = async (values: any) => {
    try {
      if (!selectedLog) return;
      
      await actionLogService.update(selectedLog.id, {
        status: values.status,
        status_comment: values.status_comment
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

  const handleReject = async (values: any) => {
    try {
      if (!selectedLog) return;
      await actionLogService.reject(selectedLog.id, { reason: values.reason });
      message.success('Action log rejected successfully');
      setRejectModalVisible(false);
      rejectForm.resetFields();
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
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'open' ? 'green' : status === 'in_progress' ? 'blue' : 'red'}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Department',
      dataIndex: 'department',
      key: 'department',
      render: (departmentId: number) => {
        const department = departments.find(d => d.id === departmentId);
        return department ? department.name : '-';
      },
    },
    {
      title: 'Assigned To',
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      render: (assigned: any) => assigned?.name || 'Unassigned',
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => format(new Date(date), 'yyyy-MM-dd HH:mm'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (text: string, record: ActionLog) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/action-logs/${record.id}`)}>
            View
          </Button>
          <Button 
            type="link" 
            onClick={() => {
              setSelectedLog(record);
              setAssignModalVisible(true);
            }}
          >
            Assign
          </Button>
          <Button
            type="link"
            onClick={() => {
              setSelectedLog(record);
              setStatusModalVisible(true);
            }}
          >
            Update Status
          </Button>
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
                  setSelectedLog(record);
                  setRejectModalVisible(true);
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

  const userColumns = [
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: 'Full Name',
      key: 'fullName',
      render: (record: User) => `${record.first_name} ${record.last_name}`,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Department',
      dataIndex: 'department',
      key: 'department',
      render: (departmentId: number) => {
        const department = departments.find(d => d.id === departmentId);
        return department ? department.name : '-';
      },
    },
    {
      title: 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role: any) => role.name,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? 'Active' : 'Inactive'}
        </Tag>
      ),
    },
  ];

  const departmentColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Units',
      key: 'units',
      render: (record: Department) => record.units?.length || 0,
    },
    {
      title: 'Users',
      key: 'users',
      render: (record: Department) => {
        const departmentUsers = users.filter(u => u.department === record.id);
        return departmentUsers.length;
      },
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
          <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
            Dashboard
          </Menu.Item>
          <Menu.Item key="actionLogs" icon={<FileTextOutlined />}>
            Action Logs
          </Menu.Item>
          <Menu.Item key="users" icon={<UserOutlined />}>
            Users
          </Menu.Item>
          <Menu.Item key="departments" icon={<TeamOutlined />}>
            Departments
          </Menu.Item>
          <Menu.Item key="settings" icon={<SettingOutlined />}>
            Settings
          </Menu.Item>
          <Menu.Item key="logout" icon={<SettingOutlined />} onClick={handleLogout}>
            Logout
          </Menu.Item>
        </Menu>
      </Sider>
      <Content style={{ padding: '24px' }}>
        <Card title="Admin Dashboard">
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane tab="Action Logs" key="actionLogs">
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
            </TabPane>

            <TabPane tab="Users" key="users">
              <Space style={{ marginBottom: 16 }}>
                <Input.Search
                  placeholder="Search users"
                  onSearch={value => setSearch(value)}
                  style={{ width: 200 }}
                />
                <Button
                  type="primary"
                  icon={<UserAddOutlined />}
                >
                  Add User
                </Button>
              </Space>

              <Table
                columns={userColumns}
                dataSource={users}
                loading={usersLoading}
                rowKey="id"
              />
            </TabPane>

            <TabPane tab="Departments" key="departments">
              <Space style={{ marginBottom: 16 }}>
                <Input.Search
                  placeholder="Search departments"
                  onSearch={value => setSearch(value)}
                  style={{ width: 200 }}
                />
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                >
                  Add Department
                </Button>
              </Space>

              <Table
                columns={departmentColumns}
                dataSource={departments}
                loading={loading}
                rowKey="id"
              />
            </TabPane>
          </Tabs>
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
          title="Reject Action Log"
          open={rejectModalVisible}
          onCancel={() => setRejectModalVisible(false)}
          footer={null}
        >
          <Form form={rejectForm} onFinish={handleReject} layout="vertical">
            <Form.Item
              name="reason"
              label="Reason"
              rules={[{ required: true, message: 'Please enter a reason' }]}
            >
              <Input.TextArea placeholder="Enter rejection reason" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit">
                Reject
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
                  <p><strong>{`${comment.user?.first_name} ${comment.user?.last_name}`}</strong> - {format(new Date(comment.created_at), 'yyyy-MM-dd HH:mm')}</p>
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

export default AdminDashboard; 