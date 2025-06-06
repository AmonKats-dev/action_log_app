import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Typography, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import styled from '@emotion/styled';
import { ROLES } from '../constants/roles';

const { Title } = Typography;

const LoginContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100vw;
  height: 100vh;
  background: #f0f2f5;
`;

const LoginCard = styled(Card)`
  width: 100%;
  max-width: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
`;

const LoginTitle = styled(Title)`
  text-align: center;
  margin-bottom: 24px !important;
`;

const Login: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login, user, isAuthenticated } = useAuth();
  const [form] = Form.useForm();

  const from = location.state?.from?.pathname || '/dashboard';

  useEffect(() => {
    if (isAuthenticated && user) {
      const userRole = user.role?.name?.toLowerCase();
      const isUnitHead = user.designation?.toLowerCase().includes('head');
      const isPasOrInUnit = user.department_unit?.id === 1 || user.department_unit?.id === 2;

      // Route based on user role and department unit
      if (isUnitHead && isPasOrInUnit) {
        navigate('/roles/senior/dashboard', { replace: true });
        return;
      }

      // Default role-based routing
      switch (userRole) {
        case ROLES.SUPER_ADMIN:
          navigate('/roles/superadmin/dashboard', { replace: true });
          break;
        case ROLES.COMMISSIONER:
        case ROLES.ASSISTANT_COMMISSIONER:
        case ROLES.ECONOMIST:
          navigate('/roles/economist/dashboard', { replace: true });
          break;
        case ROLES.PRINCIPAL_ECONOMIST:
          navigate('/roles/principal/dashboard', { replace: true });
          break;
        case ROLES.SENIOR_ECONOMIST:
          navigate('/roles/senior/dashboard', { replace: true });
          break;
        default:
          navigate('/dashboard', { replace: true });
      }
    }
  }, [isAuthenticated, user, navigate]);

  const handleSubmit = async (values: { username: string; password: string }) => {
    try {
      setIsLoading(true);
      await login(values.username, values.password);
      message.success('Login successful');
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Failed to login. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <LoginContainer>
      <LoginCard>
        <LoginTitle level={2}>Action Log System</LoginTitle>
        <Form
          form={form}
          name="login"
          onFinish={handleSubmit}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: 'Please input your username!' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Username"
              disabled={isLoading}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Please input your password!' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Password"
              disabled={isLoading}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={isLoading}
              block
            >
              Log in
            </Button>
          </Form.Item>
        </Form>
      </LoginCard>
    </LoginContainer>
  );
};

export default Login; 