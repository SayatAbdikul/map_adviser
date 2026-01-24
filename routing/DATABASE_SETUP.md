# Database Setup Guide

This guide will help you set up the PostgreSQL database with Supabase for the Map Adviser application.

## Prerequisites

- Supabase account and project
- Python 3.8+ installed
- Access to your Supabase database password

## Step 1: Add Database Password to Environment

1. Open or create `.env` file in the `routing` directory:
   ```bash
   cd /home/martian/Documents/swe/pet-projects/map_adviser/routing
   ```

2. Add your Supabase database password:
   ```env
   SUPABASE_DB_PASSWORD=your_actual_password_here
   ```

3. Keep your existing API keys (DOUBLEGIS_API_KEY, GEMINI_API_KEY)

## Step 2: Install Dependencies

Install the new dependencies (asyncpg, bcrypt, psycopg2-binary):

```bash
cd /home/martian/Documents/swe/pet-projects/map_adviser/routing
pip install -r requirements.txt
```

## Step 3: Run Database Migrations

You mentioned you'll run migrations yourself. Here's how:

### Option A: Using Supabase SQL Editor (Recommended)

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `migrations/001_create_users_table.sql`
4. Click "Run" to execute
5. Repeat for `migrations/002_create_messages_table.sql`

### Option B: Using psql Command Line

```bash
# Connect to your Supabase database
psql "postgresql://postgres:YOUR_PASSWORD@db.forsqzgswpmzpkjmkvlf.supabase.co:5432/postgres"

# Run migrations
\i migrations/001_create_users_table.sql
\i migrations/002_create_messages_table.sql

# Verify tables were created
\dt
```

## Step 4: Start the Server

```bash
cd /home/martian/Documents/swe/pet-projects/map_adviser/routing
uvicorn main:app --reload --port 8000
```

You should see:
```
✓ Database connection pool created successfully
```

## Step 5: Test the Endpoints

### Test POST /api/messages (Send a message)

```bash
curl -X POST http://localhost:8000/api/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello from user",
    "role": "user"
  }'
```

Expected response:
```json
{
  "id": "uuid-here",
  "user_id": null,
  "message": "Hello from user",
  "role": "user",
  "created_at": "2026-01-24T17:03:30.123456+00:00"
}
```

### Test GET /api/messages (Fetch messages)

```bash
curl http://localhost:8000/api/messages?limit=10
```

Expected response:
```json
{
  "messages": [
    {
      "id": "uuid-here",
      "user_id": null,
      "message": "Hello from user",
      "role": "user",
      "created_at": "2026-01-24T17:03:30.123456+00:00"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### Test with Bot Message

```bash
curl -X POST http://localhost:8000/api/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I can help you plan routes!",
    "role": "bot"
  }'
```

## API Documentation

Once the server is running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

## Troubleshooting

### Connection Error
If you see database connection errors:
1. Verify `SUPABASE_DB_PASSWORD` is set correctly in `.env`
2. Check your Supabase project is active
3. Verify the connection string in `database.py` matches your Supabase details

### Migration Errors
If migrations fail:
1. Check if tables already exist: `\dt` in psql
2. Drop tables if needed: `DROP TABLE messages CASCADE; DROP TABLE users CASCADE;`
3. Re-run migrations

### Import Errors
If you get import errors:
1. Make sure you're in the correct directory
2. Verify all dependencies are installed: `pip list | grep -E "asyncpg|bcrypt|psycopg2"`

## Database Schema

### Users Table
- `id` (UUID) - Primary key
- `username` (VARCHAR) - Unique, 3-50 characters
- `email` (VARCHAR) - Unique, validated format
- `password_hash` (VARCHAR) - Bcrypt hashed password
- `created_at`, `updated_at` - Timestamps

### Messages Table
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users (nullable for bot messages)
- `message` (TEXT) - Message content (max 10,000 chars)
- `role` (ENUM) - 'user' or 'bot'
- `created_at` - Timestamp

## Next Steps

The authentication system is ready but not yet integrated with endpoints. You can:
1. Add user registration endpoint using `AuthService.create_user()`
2. Add login endpoint using `AuthService.authenticate_user()`
3. Implement JWT tokens for session management
4. Link messages to authenticated users

For now, messages can be sent without authentication (user_id is optional).
