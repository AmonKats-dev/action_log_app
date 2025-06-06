import React from 'react';
import { Typography, Box } from '@mui/material';

const Users: React.FC = () => (
  <Box p={3}>
    <Typography variant="h4">Users</Typography>
    <Typography variant="body1" mt={2}>
      List of users will appear here.
    </Typography>
  </Box>
);

export default Users; 