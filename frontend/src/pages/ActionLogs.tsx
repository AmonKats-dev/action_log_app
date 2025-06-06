import { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { actionLogService } from '../services/actionLogService';
import { ActionLog } from '../types/actionLog';
import { Button, Card, Table, Modal, Form, Input, message, Space, Tag } from 'antd';
import { PlusOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { format } from 'date-fns';

const ActionLogs = () => {
  const { user } = useAuth();
  const [actionLogs, setActionLogs] = useState<ActionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [rejectModalVisible, setRejectModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState<ActionLog | null>(null);
  const [form] = Form.useForm();
  const [rejectForm] = Form.useForm();

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

  useEffect(() => {
    fetchActionLogs();
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
      case 'pending':
        return 'warning';
      case 'approved':
        return 'success';
      case 'rejected':
        return 'error';
      default:
        return 'default';
    }
  };

  const columns = [
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: 'Department',
      dataIndex: ['department', 'name'],
      key: 'department',
    },
    {
      title: 'Created By',
      dataIndex: ['created_by', 'username'],
      key: 'created_by',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => format(new Date(date), 'PPpp'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record: ActionLog) => (
        <Space>
          {record.can_approve && record.status === 'pending' && (
            <>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record)}
              >
                Approve
              </Button>
              <Button
                danger
                icon={<CloseOutlined />}
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

  return (
    <div>
      <Card
        title="Action Logs"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            Create Action Log
          </Button>
        }
      >
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
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item
            name="department_id"
            label="Department"
            rules={[{ required: true, message: 'Please select a department' }]}
          >
            <Input type="number" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              Create
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
            name="rejection_reason"
            label="Rejection Reason"
            rules={[{ required: true, message: 'Please enter a rejection reason' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" danger>
              Reject
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ActionLogs; 