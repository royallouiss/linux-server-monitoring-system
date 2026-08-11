# Linux Server Monitoring System

## Development Environment Setup Guide

This guide explains how to set up the project on a new computer.

---

# Prerequisites

Install the following software before cloning the project.

- Git
- Python 3.13+
- PostgreSQL
- VS Code
- UV Package Manager

---

# Clone the Repository

```bash
git clone https://github.com/royallouiss/linux-server-monitoring-system.git

cd linux-server-monitoring-system
```

---

# Create the Virtual Environment

Install all project dependencies.

```bash
uv sync
```

---

# Configure Environment Variables

Create a file named:

.env

Use the following template.

```env
DJANGO_READ_DOT_ENV_FILE=True

POSTGRES_DB=linux_monitoring
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Replace:

your_password

with your PostgreSQL password.

---

# Create PostgreSQL Database

Create a database named:

linux_monitoring

---

# Apply Database Migrations

```bash
python manage.py migrate
```

---

# Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts.

---

# Run the Development Server

```bash
python manage.py runserver
```

Open:

http://127.0.0.1:8000

Admin Panel:

http://127.0.0.1:8000/admin

---

# Verify Installation

If the following work correctly, the setup is complete.

- Homepage loads successfully
- Admin page opens
- Superuser login works