# Action Log System

A comprehensive web-based system for tracking and managing action items across departmental units in the Public Accountability and Performance (PAP) Department.

## Project Structure

```
action-log-system/
├── frontend/           # React + Vite frontend application
├── backend/           # Django backend API
└── docs/             # Project documentation
```

## Prerequisites

- Node.js (v16 or higher)
- Python (v3.8 or higher)
- MySQL (v8.0 or higher)
- pip (Python package manager)
- npm (Node package manager)

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure MySQL database:
   - Database name: action_log_db
   - Update database settings in `backend/config/settings.py`

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Start the development server:
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

## Features

- Role-based access control
- Action log creation and management
- Multi-officer assignments
- Approval workflow
- Reporting and dashboards
- Audit trails
- LDAP integration

## Technology Stack

- Frontend: React + Vite
- Backend: Django REST Framework
- Database: MySQL
- Authentication: LDAP/Active Directory

## Development Team

- Project Manager
- System Analysts
- Developers
- Database Administrator
- QA/Testers

## License

This project is proprietary and confidential. 