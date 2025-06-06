import React from 'react';
import { Avatar, Typography, Space } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import { User } from '../types/user';

const { Text } = Typography;

interface UserDisplayProps {
  user: User;
}

const UserDisplay: React.FC<UserDisplayProps> = ({ user }) => {
  return (
    <div style={{ 
      padding: '24px 16px',
      textAlign: 'center',
      borderBottom: '1px solid #f0f0f0'
    }}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Avatar 
          size={64} 
          icon={<UserOutlined />} 
          style={{ 
            backgroundColor: '#1890ff',
            marginBottom: '8px'
          }}
        />
        <Text strong style={{ 
          fontSize: '16px',
          display: 'block',
          textAlign: 'center'
        }}>
          {user.first_name} {user.last_name}
        </Text>
        <Text type="secondary" style={{ 
          fontSize: '14px',
          display: 'block',
          textAlign: 'center'
        }}>
          {user.designation}
        </Text>
      </Space>
    </div>
  );
};

export default UserDisplay; 