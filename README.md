# Zorvyn Finance Data

A high-performance financial data management system built with FastAPI, PostgreSQL, Redis, and React (Vite).

## 🚀 Features

- **FastAPI Backend**: High-performance Python backend with dependency injection and Pydanic models.
- **Async Database Access**: Uses SQLAlchemy with `asyncpg` for non-blocking database queries.
- **Redis Integration**: Real-time data caching and session management.
- **React Frontend**: Modern UI built with React 19, Redux Toolkit, and Tailwind CSS.
- **uv Package Manager**: Blazing fast Python dependency management.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** (Python package manager)
- **Node.js (LTS)** & **npm**
- **PostgreSQL** (Running instance)
- **Redis** (Running instance)

---

## 📥 Getting Started

### 1. Clone the Repository
```bash
git clone <repository-url>
cd zorvyn
```

### 2. Backend Setup (`uv`)

Navigate to the `backend` directory and install dependencies using `uv`:

```bash
cd backend
# Create a virtual environment and install dependencies
uv sync
```

#### Configure Environment Variables
Create a `.env` file in the `backend` directory (or copy from `.env` if provided):
```bash
# Example .env configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=zorvyn-DB
DB_USER=admin
DB_PASSWORD=root
SECRET_KEY=your_very_secret_key
REDIS_URL=redis://localhost:6379/0
```

#### Database Migrations
Run Alembic migrations to set up your database schema:
```bash
uv run alembic upgrade head
```

#### Start the Backend Server
```bash
uv run uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`.

---

### 3. Frontend Setup (React + Vite)

The frontend is located within the `backend/frontend` directory.

```bash
cd backend/frontend
# Install dependencies
npm install
# Start the development server
npm run dev
```
The frontend will be available at `http://localhost:3000` (check the output for the exact port).

---

## 🏗️ Project Structure

- `backend/`: Core FastAPI application.
  - `app/`: Application logic (modules, core, database).
  - `alembic/`: Database migrations.
  - `frontend/`: React application (Vite-based).
- `pyproject.toml`: Modern Python project configuration.
- `uv.lock`: Deterministic lockfile for Python dependencies.

## 🧪 Running Tests

To run backend tests, use `pytest` via `uv`:
```bash
cd backend
uv run pytest
```

---

## 📊 Test Execution Summary

Current test results for the backend suite:

- **Total Tests**: 466
- **Passed**: 322 ✅
- **Failed**: 41 ❌
- **Errors**: 103 ⚠️

---


