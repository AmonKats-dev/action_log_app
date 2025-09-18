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

const SeniorDashboard: React.FC = () => {
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
  const [selectedLogComments, setSelectedLogComments] = useState<any[]>([]);
  const [commentsModalVisible, setCommentsModalVisible] = useState(false);
  const [commentsLoading, setCommentsLoading] = useState(false);

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
    if (!user) return;

    try {
      setUsersLoading(true);
      const data = await userService.getByDepartment(user.department);
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

  const handleViewComments = async (logId: number) => {
    try {
      setCommentsLoading(true);
      const response = await actionLogService.getComments(logId);
      setSelectedLogComments(response);
      setCommentsModalVisible(true);
    } catch (error) {
      console.error('Error fetching comments:', error);
      message.error('Failed to fetch comments');
    } finally {
      setCommentsLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleMenuClick = (e: any) => {
    setSelectedMenuKey(e.key);
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
      render: (text: string, record: ActionLog) => {
        const isUnitHead = user.designation?.toLowerCase().includes('head');
        const isPasOrInUnit = user.department_unit?.id === 1 || user.department_unit?.id === 2;
        const recordDepartmentUnit = record.department.units.find(unit => unit.id === user.department_unit?.id);
        const canAssign = isUnitHead && isPasOrInUnit && recordDepartmentUnit;

        console.log('User data:', {
          isUnitHead,
          isPasOrInUnit,
          userDepartmentUnit: user.department_unit,
          recordDepartmentUnit,
          canAssign
        });

        return (
          <Space>
            <Button type="link" onClick={() => navigate(`/action-logs/${record.id}`)}>
              View
            </Button>
            {canAssign && (
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
            <Button
              type="link"
              onClick={() => handleViewComments(record.id)}
            >
              Comments
            </Button>
          </Space>
        );
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
          items={[
            {
              key: 'actionLogs',
              icon: <FileTextOutlined />,
              label: 'Action Logs'
            },
            {
              key: 'logout',
              icon: <SettingOutlined />,
              label: 'Logout',
              onClick: handleLogout
            }
          ]}
        />
      </Sider>
      <Content style={{ padding: '24px' }}>
        <Card title="Senior Staff Dashboard">
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
              rules={[{ required: true, message: 'Please select at least one assignee' }]}
            >
              <Select mode="multiple" loading={usersLoading}>
                {users.map(user => (
                  <Select.Option key={user.id} value={user.id.toString()}>
                    {user.first_name} {user.last_name}
                  </Select.Option>
                ))}
              </Select>
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
      </Content>
    </Layout>
  );
};

export default SeniorDashboard; 