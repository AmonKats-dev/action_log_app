import React from 'react';
import { Typography, Box } from '@mui/material';

const Departments: React.FC = () => (
  <Box p={3}>
    <Typography variant="h4">Departments</Typography>
    <Typography variant="body1" mt={2}>
      List of departments will appear here.
    </Typography>
  </Box>
);

export default Departments; 