import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { RoleType } from '../constants/roles';

interface RoleProtectedRouteProps {
  allowedRoles: RoleType[];
}

const RoleProtectedRoute = ({ allowedRoles }: RoleProtectedRouteProps) => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const userRole = user.role?.name?.toLowerCase() as RoleType;
  if (!allowedRoles.includes(userRole)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
};

export default RoleProtectedRoute; 