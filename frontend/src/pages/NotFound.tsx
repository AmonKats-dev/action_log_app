import React from 'react';
import { Typography, Box } from '@mui/material';

const NotFound: React.FC = () => (
  <Box p={3} textAlign="center">
    <Typography variant="h3" color="error">404</Typography>
    <Typography variant="h5">Page Not Found</Typography>
  </Box>
);

export default NotFound; 