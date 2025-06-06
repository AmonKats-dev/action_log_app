import React, { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import { actionLogService } from '../../services/actionLogService';
import { departmentService } from '../../services/departmentService';
import { ActionLog } from '../../types/actionLog';
import { Department } from '../../types/department';
import { Button, Card, Table, Modal, Form, Input, message, Space, Tag, Select, DatePicker } from 'antd';
import { PlusOutlined, CheckOutlined, CloseOutlined, FilterOutlined, UserAddOutlined } from '@ant-design/icons';
import { format } from 'date-fns';
import './economistDashboard.css';
import { useNavigate } from 'react-router-dom';

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

const ActionLogs = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [actionLogs, setActionLogs] = useState<ActionLog[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<ActionLog | null>(null);
  const [form] = Form.useForm();
  const [rejectForm] = Form.useForm();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchActionLogs = async () => {
    try {
      const data = await actionLogService.getAll();
      setActionLogs(data);
    } catch (error) {
      message.error('Failed to fetch action logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchDepartments = async () => {
    try {
      const data = await departmentService.getAll();
      setDepartments(data);
    } catch (error) {
      message.error('Failed to fetch departments');
    }
  };

  useEffect(() => {
    fetchActionLogs();
    fetchDepartments();
  }, []);

  const handleCreate = async (values: any) => {
    try {
      await actionLogService.create(values);
      message.success('Action log created successfully');
      setCreateModalVisible(false);
      form.resetFields();
      fetchActionLogs();
    } catch (error) {
      message.error('Failed to create action log');
    }
  };

  const handleApprove = async (log: ActionLog) => {
    try {
      await actionLogService.approve(log.id);
      message.success('Action log approved successfully');
      fetchActionLogs();
    } catch (error) {
      message.error('Failed to approve action log');
    }
  };

  const handleReject = async (values: any) => {
    if (!selectedLog) return;
    try {
      await actionLogService.reject(selectedLog.id, values);
      message.success('Action log rejected successfully');
      setRejectModalVisible(false);
      rejectForm.resetFields();
      fetchActionLogs();
    } catch (error) {
      message.error('Failed to reject action log');
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

  // Filter and search logic
  const filteredLogs = actionLogs.filter(log => {
    const matchesSearch =
      log.title.toLowerCase().includes(search.toLowerCase()) ||
      log.description.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter ? log.status === statusFilter : true;
    return matchesSearch && matchesStatus;
  });

  const columns = [
    {
      title: 'TITLE',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <b>{text}</b>,
    },
    {
      title: 'DESCRIPTION',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'STATUS',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)} style={{ fontWeight: 500 }}>
          {status === 'open' ? 'Open' : status === 'in_progress' ? 'In Progress' : status.charAt(0).toUpperCase() + status.slice(1)}
        </Tag>
      ),
    },
    {
      title: 'DUE DATE',
      dataIndex: 'due_date',
      key: 'due_date',
      render: (date: string) => date ? format(new Date(date), 'yyyy-MM-dd') : '',
    },
    {
      title: 'ASSIGNED TO',
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      render: (assigned: string[]) => assigned ? assigned.join(', ') : '',
    },
    {
      title: 'ACTIONS',
      key: 'actions',
      render: (_: unknown, record: ActionLog) => (
        <Space>
          <Button type="link" icon={<CheckOutlined />} disabled>Update</Button>
        </Space>
      ),
    },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="economist-dashboard-bg">
      <Card className="economist-dashboard-header">
        <div className="dashboard-header-content">
          <div className="dashboard-title-row">
            <UserAddOutlined style={{ fontSize: 32 }} />
            <span className="dashboard-title">Economist Dashboard</span>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              size="large"
              className="create-action-log-btn"
              onClick={() => setCreateModalVisible(true)}
            >
              Create Action Log
            </Button>
            <Button
              type="default"
              onClick={handleLogout}
              className="logout-btn"
              style={{ borderRadius: 8, fontWeight: 500 }}
            >
              Logout
            </Button>
          </div>
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

      <Card className="economist-dashboard-table-card">
        <Table
          columns={columns}
          dataSource={filteredLogs}
          loading={loading}
          rowKey="id"
          pagination={false}
          className="dashboard-table"
        />
      </Card>

      <Modal
        title={<span className="modal-title">Create New Action Log</span>}
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={600}
        className="dashboard-modal"
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <div className="modal-row">
            <Form.Item
              name="title"
              label="Title"
              className="modal-form-item"
              rules={[{ required: true, message: 'Enter action log title' }]}
            >
              <Input placeholder="Enter action log title" />
            </Form.Item>
            <Form.Item
              name="department_id"
              label="Departmental Unit"
              className="modal-form-item"
              rules={[{ required: true, message: 'Select a department' }]}
            >
              <Select
                placeholder="Select unit"
                options={departments.map(dept => ({ label: dept.name, value: dept.id }))}
              />
            </Form.Item>
          </div>
          <Form.Item
            name="description"
            label="Description"
            className="modal-form-item"
            rules={[{ required: true, message: 'Provide detailed description of the action item' }]}
          >
            <Input.TextArea rows={4} placeholder="Provide detailed description of the action item" />
          </Form.Item>
          <div className="modal-row">
            <Form.Item
              name="due_date"
              label="Due Date"
              className="modal-form-item"
              rules={[{ required: true, message: 'Select due date' }]}
            >
              <DatePicker style={{ width: '100%' }} placeholder="mm/dd/yyyy" />
            </Form.Item>
            <Form.Item
              name="priority"
              label="Priority"
              className="modal-form-item"
              rules={[{ required: true, message: 'Select priority' }]}
            >
              <Select options={priorities} placeholder="Low" />
            </Form.Item>
          </div>
          <Form.Item
            name="assigned_to"
            label="Assign To"
            className="modal-form-item"
            rules={[{ required: true, message: 'Select at least one assignee' }]}
          >
            <Select
              mode="multiple"
              placeholder="Select users"
              options={mockUsers.map(name => ({ label: name, value: name }))}
              style={{ minHeight: 80 }}
            />
          </Form.Item>
          <Form.Item name="attachments" label="Attachments" valuePropName="fileList" getValueFromEvent={e => Array.isArray(e) ? e : e && e.fileList} className="modal-form-item">
            <Input type="file" multiple />
          </Form.Item>
          <div className="modal-footer-row">
            <Button onClick={() => setCreateModalVisible(false)} className="modal-cancel-btn">
              Cancel
            </Button>
            <Button type="primary" htmlType="submit" className="modal-create-btn">
              Create Action Log
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default ActionLogs; 