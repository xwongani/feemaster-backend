# Test Files

This folder contains test scripts for the Fee Master backend system.

## Files

### `debug_students.py`
Tests direct database connections and student data queries.

**Usage:**
```bash
cd backend
.\.venv\Scripts\python.exe tests/debug_students.py
```

**What it tests:**
- Direct Supabase table queries
- Student data retrieval
- Status counting

### `test_raw_query.py`
Tests the `execute_raw_query` function with various SQL queries.

**Usage:**
```bash
cd backend
.\.venv\Scripts\python.exe tests/test_raw_query.py
```

**What it tests:**
- Raw SQL execution through Supabase RPC
- Student count queries
- Grade distribution queries
- Payment data queries

### `test_dashboard_endpoints.py`
Tests all dashboard API endpoints through HTTP requests.

**Usage:**
```bash
cd backend
# Make sure the server is running first:
# .\.venv\Scripts\python.exe -m uvicorn main:app --reload

# Then in another terminal:
pip install aiohttp  # if not already installed
.\.venv\Scripts\python.exe tests/test_dashboard_endpoints.py
```

**What it tests:**
- `/api/v1/dashboard/stats` endpoint
- `/api/v1/dashboard/grade-distribution` endpoint  
- `/api/v1/dashboard/quick-actions` endpoint
- `/api/v1/dashboard/revenue-chart` endpoint

## Requirements

These test files require:
- Active backend server (for endpoint tests)
- Valid Supabase connection (configured in `.env`)
- Python virtual environment activated
- `aiohttp` package (for HTTP endpoint tests)

## Notes

- Make sure your `.env` file has valid Supabase credentials
- The `execute_sql` function must be created in your Supabase database
- Some tests may return fallback data if the database is empty 