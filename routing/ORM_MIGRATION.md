# SQLAlchemy ORM Migration Guide

The database layer has been rewritten to use **SQLAlchemy ORM** instead of raw SQL queries.

## What Changed

### 1. **Database Connection** (`database.py`)
- ✅ Now uses SQLAlchemy async engine
- ✅ Host is configurable via environment variables (not hardcoded)
- ✅ Session-based approach with automatic transaction management
- ✅ Connection pooling built-in

### 2. **ORM Models** (`db_models.py`) - **NEW**
- ✅ `User` model with SQLAlchemy declarative base
- ✅ `Message` model with relationships
- ✅ All indexes and constraints defined in models

### 3. **Services Rewritten**
- ✅ `auth_service.py` - All queries now use SQLAlchemy ORM
- ✅ `chat_service.py` - All queries now use SQLAlchemy ORM
- ✅ No more raw SQL strings

### 4. **Environment Configuration**
Database host is now configurable and not exposed in code:

```env
# Required
SUPABASE_DB_PASSWORD=your_password

# Optional (defaults set in code)
SUPABASE_DB_HOST=your_db_host
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
```

## Installation

Install updated dependencies:

```bash
cd /home/martian/Documents/swe/pet-projects/map_adviser/routing
pip install -r requirements.txt
```

New packages added:
- `SQLAlchemy==2.0.25` - ORM framework
- `alembic==1.13.1` - Database migrations tool

## Database Setup

### Option 1: Keep Existing SQL Migrations
Your tables should already exist if you ran the SQL migrations. The ORM will work with them.

### Option 2: Create Tables with ORM (Development)
```python
from database import db

# One-time table creation
await db.connect()
await db.create_tables()
await db.disconnect()
```

## Usage Examples

### Before (Raw SQL)
```python
# Old way
query = "SELECT * FROM messages WHERE role = $1 ORDER BY created_at DESC LIMIT $2"
messages = await db.fetch(query, 'user', 10)
```

### After (SQLAlchemy ORM)
```python
# New way
from sqlalchemy import select
from db_models import Message

async with db.get_session() as session:
    stmt = select(Message).where(Message.role == 'user').order_by(Message.created_at.desc()).limit(10)
    result = await session.execute(stmt)
    messages = result.scalars().all()
```

## Key ORM Benefits

1. **Type Safety**: IDE autocomplete for model fields
2. **No SQL Injection**: Parameters are automatically escaped
3. **Relationship Navigation**: Access related objects easily
4. **Database Agnostic**: Easier to switch databases if needed
5. **Migration Support**: Alembic can auto-generate migrations from model changes

## Session Management

All service methods now use `async with db.get_session()` pattern:

```python
async with db.get_session() as session:
    # Automatic transaction
    session.add(new_object)
    await session.commit()
    # Auto rollback on exception
    # Auto close session
```

## Testing

Run the updated test script:

```bash
python test_database.py
```

It will test:
- ✅ Database connection with ORM
- ✅ Saving messages via ORM
- ✅ Fetching messages via ORM

## Next Steps

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Update .env**: Add any custom database config if needed
3. **Test**: Run `python test_database.py`
4. **Start server**: `uvicorn main:app --reload --port 8000`

The API endpoints remain the same - only the internal implementation changed to ORM!
