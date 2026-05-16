# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**JobHub** is an internal recruitment application (desktop + API) built as a university group project (N21-D31). The application consists of:

- **FastAPI API server** (`server/`) with MySQL database
- **PySide6 (Qt6) desktop client** (`client/`)

## Development Commands

### Server (FastAPI)
```bash
cd server
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health
- Seed admin: `python -m scripts.seed_admin`

### Client (PySide6)
```bash
cd client
pip install -r requirements.txt
python main.py
```
- Requires server to be running first
- Demo mode: Set `USE_MOCK_DATA=1` in `client/.env` (no backend needed)

### Database
```bash
# Create database
mysql -u root -p jobhub < database/schema.sql

# Seed sample data
mysql -u root -p jobhub < database/seed_data_x10.sql
```

## Architecture

### Server (`server/app/`)
- **Entry**: `main.py` - FastAPI app with `/api` prefix for all routes
- **Routers**: `routers/` - `auth.py` (login/register), `hr.py` (HR endpoints), `candidate.py` (candidate endpoints), `admin.py` (admin management), `users.py` (user profile)
- **Models**: SQLAlchemy models in `models/` (user, job, application, CV, notification, invoice)
- **Config**: `config.py` - Pydantic Settings, reads from `.env`
- **DB**: `db.py` - SQLAlchemy engine + session management, MySQL schema patches

### Client (`client/app/`)
- **Entry**: `main.py` - PySide6 application launcher
- **API Client**: `client/jobhub_api.py` - All HTTP calls to backend; falls back to mock data
- **UI**: `ui/` - PySide6 widgets organized by dashboard:
  - `auth_window.py` - Login/Register
  - `hr_dashboard.py` - HR dashboard (job management, candidate review)
  - `user_dashboard.py` - Candidate dashboard (job search, CV management)
  - `admin_dashboard.py` - Admin dashboard (user management, job approval)
- **Config**: `config.py` - Reads `API_BASE_URL`, `USE_MOCK_DATA`, `UI_THEME` from `.env`
- **Theme**: `theme.py` - Global colors and fonts

### Database Schema
- `database/schema.sql` - Core tables (users, jobs, applications, CVs)
- `database/seed_data_x10.sql` - Sample data for testing

## Branch Strategy

Work on separate branches for `server` and `client` features. Merge to `master` only after testing, then push.

## Environment Files

Both server and client require `.env` files (copy from `.env.example`):
- `server/.env` - MySQL connection, JWT secret
- `client/.env` - API URL, mock mode, UI theme
