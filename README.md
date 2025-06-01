# Fee Master Backend

A comprehensive FastAPI backend for school fee management system with payment processing, student management, financial reporting, and integrations.

## Features

- **Student Management**: Complete CRUD operations, enrollment tracking, and academic records
- **Payment Processing**: Multiple payment methods, receipt generation, and status tracking
- **Financial Dashboard**: Real-time analytics, revenue tracking, and financial reporting
- **Reporting System**: Comprehensive reports with CSV export capabilities
- **Integrations**: QuickBooks, WhatsApp, SMS, and email notifications
- **User Management**: Role-based access control with JWT authentication
- **Settings Management**: Configurable system settings and preferences

## Tech Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL / Supabase
- **Authentication**: JWT with bcrypt password hashing
- **Validation**: Pydantic models
- **Documentation**: Auto-generated OpenAPI/Swagger docs

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

**Option A: PostgreSQL**
```bash
# Install PostgreSQL and create database
createdb feemaster

# Run the schema
psql -d feemaster -f schema.sql
```

**Option B: Supabase**
1. Create a new project at [supabase.com](https://supabase.com)
2. Copy the SQL from `schema.sql` and run it in the Supabase SQL editor
3. Update your `.env` file with Supabase credentials

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

Key settings to configure:
- `DATABASE_URL` or Supabase credentials
- `SECRET_KEY` (generate a secure random key)
- Email/SMS/WhatsApp settings (optional)

### 4. Run the Application

```bash
# Start the development server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Documentation

### Authentication

All API endpoints require authentication except:
- `POST /api/v1/auth/login`
- `GET /health`
- `GET /`

**Login to get access token:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@feemaster.edu", "password": "admin123"}'
```

**Use token in subsequent requests:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/students"
```

### Default Admin User

- **Email**: admin@feemaster.edu
- **Password**: admin123
- **Role**: super_admin

⚠️ **Change the default password in production!**

## API Endpoints Overview

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/logout` - User logout

### Students
- `GET /api/v1/students` - List students with filtering
- `POST /api/v1/students` - Create new student
- `GET /api/v1/students/{id}` - Get student details
- `PUT /api/v1/students/{id}` - Update student
- `DELETE /api/v1/students/{id}` - Delete student
- `POST /api/v1/students/bulk-import` - Bulk import from CSV

### Payments
- `GET /api/v1/payments` - List payments with filtering
- `POST /api/v1/payments` - Create new payment
- `GET /api/v1/payments/{id}` - Get payment details
- `PUT /api/v1/payments/{id}/status` - Update payment status
- `GET /api/v1/payments/{id}/receipt` - Get payment receipt

### Dashboard
- `GET /api/v1/dashboard/stats` - Dashboard statistics
- `GET /api/v1/dashboard/recent-activities` - Recent payment activities
- `GET /api/v1/dashboard/financial-summary` - Financial summary
- `GET /api/v1/dashboard/revenue-chart` - Revenue chart data

### Reports
- `GET /api/v1/reports/financial` - Financial reports
- `GET /api/v1/reports/student` - Student reports
- `GET /api/v1/reports/payment` - Payment reports
- `GET /api/v1/reports/outstanding-fees` - Outstanding fees report

### Settings
- `GET /api/v1/settings/general` - General settings
- `PUT /api/v1/settings/general` - Update general settings
- `GET /api/v1/settings/payment-options` - Payment settings
- `GET /api/v1/settings/users` - User management

### Integrations
- `GET /api/v1/integrations` - List all integrations
- `GET /api/v1/integrations/{id}` - Get integration details
- `POST /api/v1/integrations/{id}/connect` - Connect integration
- `POST /api/v1/integrations/{id}/test` - Test integration

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── schema.sql             # Database schema
├── .env                   # Environment configuration
├── .env.example           # Environment template
├── app/
│   ├── config.py          # Application configuration
│   ├── models.py          # Pydantic models
│   ├── database.py        # Database abstraction layer
│   ├── routes/           # API route modules
│   │   ├── auth.py        # Authentication routes
│   │   ├── students.py    # Student management
│   │   ├── payments.py    # Payment processing
│   │   ├── dashboard.py   # Dashboard data
│   │   ├── reports.py     # Reporting system
│   │   ├── integrations.py # External integrations
│   │   └── settings.py    # System settings
│   └── services/         # Business logic services
│       ├── notification_service.py  # Email/SMS/WhatsApp
│       ├── receipt_service.py       # Receipt generation
│       └── analytics_service.py     # Data analytics
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/feemaster
# OR use Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# Security
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Features
ENABLE_NOTIFICATIONS=true
ENABLE_RECEIPTS=true
ENABLE_INTEGRATIONS=true
```

### School Settings

Configure school-specific settings:

```env
SCHOOL_NAME=Your School Name
SCHOOL_EMAIL=info@yourschool.edu
SCHOOL_PHONE=+260 XXX XXX XXX
SCHOOL_ADDRESS=Your School Address
SCHOOL_CURRENCY=ZMW
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Quality

```bash
# Install development dependencies
pip install black isort flake8

# Format code
black .
isort .

# Check code quality
flake8 .
```

### Database Migrations

For schema changes:

1. Update `schema.sql`
2. Create migration scripts in `migrations/` folder
3. Apply changes to your database

## Deployment

### Production Checklist

- [ ] Change default admin password
- [ ] Use strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up HTTPS/SSL
- [ ] Configure email/SMS providers
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Setup

```bash
# Production environment
export DEBUG=false
export DATABASE_URL=postgresql://prod-user:prod-pass@prod-host/feemaster
export SECRET_KEY=your-production-secret-key
```

## Integration Examples

### QuickBooks Integration

```python
# Connect QuickBooks
POST /api/v1/integrations/quickbooks/connect
{
  "client_id": "your-qb-client-id",
  "client_secret": "your-qb-client-secret",
  "environment": "production"
}
```

### WhatsApp Notifications

```python
# Configure WhatsApp
WHATSAPP_API_URL=https://api.whatsapp.com
WHATSAPP_API_KEY=your-api-key
WHATSAPP_PHONE_NUMBER=+260971234567
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check DATABASE_URL format
   - Verify database server is running
   - Check firewall settings

2. **Authentication Issues**
   - Verify SECRET_KEY is set
   - Check token expiration time
   - Ensure proper Authorization header format

3. **CORS Issues**
   - Update CORS_ORIGINS in .env
   - Check frontend URL matches CORS settings

### Logs

Application logs are written to:
- Console output (development)
- `app.log` file
- System logs (production)

### Support

For technical support:
- Check the `/docs` endpoint for API documentation
- Review logs for error details
- Check GitHub issues for known problems

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here] 