import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import ProtectedRoute from './auth/ProtectedRoute';
import RoleProtectedRoute from './auth/RoleProtectedRoute';
import Login from './pages/Login';
import ActionLogs from './pages/ActionLogs';
import Users from './pages/Users';
import Departments from './pages/Departments';
import { ROLES } from './constants/roles';
import { 
  EconomistDashboard,
  // SeniorDashboard,
  // PrincipalDashboard,
  // AssistantDashboard,
  // CommissionerDashboard 
} from './pages/roles';

const App = () => {
  const { user } = useAuth();

  const getDashboardForRole = () => {
    if (!user) return <Navigate to="/login" replace />;

    switch (user.role?.name?.toLowerCase()) {
      case ROLES.ECONOMIST:
      case ROLES.COMMISSIONER:
      case ROLES.ASSISTANT_COMMISSIONER:
        return <Navigate to="/roles/economist/dashboard" replace />;
      case ROLES.SENIOR_ECONOMIST:
        // return <Navigate to="/roles/senior/dashboard" replace />;
      case ROLES.PRINCIPAL_ECONOMIST:
        // return <Navigate to="/roles/principal/dashboard" replace />;
      default:
        return <Navigate to="/login" replace />;
    }
  };

  return (
    <Routes>
      <Route path="/login" element={
        user ? getDashboardForRole() : <Login />
      } />
      
      <Route element={<ProtectedRoute />}>
        <Route index element={getDashboardForRole()} />
        <Route path="dashboard" element={getDashboardForRole()} />
        <Route path="action-logs" element={<ActionLogs />} />
      </Route>

      {/* Role-specific dashboard routes */}
      <Route path="/roles/economist/dashboard" element={<EconomistDashboard />} />
      {/* <Route path="/roles/senior/dashboard" element={<SeniorDashboard />} />
      <Route path="/roles/principal/dashboard" element={<PrincipalDashboard />} />
      <Route path="/roles/assistant/dashboard" element={<AssistantDashboard />} />
      <Route path="/roles/commissioner/dashboard" element={<CommissionerDashboard />} /> */}

      <Route element={<RoleProtectedRoute allowedRoles={[ROLES.COMMISSIONER, ROLES.ASSISTANT_COMMISSIONER, ROLES.SUPER_ADMIN]} />}>
        <Route path="users" element={<Users />} />
      </Route>

      <Route element={<RoleProtectedRoute allowedRoles={[ROLES.COMMISSIONER, ROLES.SUPER_ADMIN]} />}>
        <Route path="departments" element={<Departments />} />
      </Route>
    </Routes>
  );
};

export default App; 