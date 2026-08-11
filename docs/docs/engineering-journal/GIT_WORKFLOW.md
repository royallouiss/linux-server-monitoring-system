# Git Workflow Guide

## Linux Server Monitoring System

This document explains how our team will use Git and GitHub during development.

---

# Branch Strategy

We use a feature branch workflow.

```
main
│
├── feature/servers
├── feature/dashboard
├── feature/monitoring
├── feature/reports
└── feature/alerts
```

- `main` always contains stable and working code.
- Every new feature is developed in its own branch.
- Never commit directly to `main`.

---

# Initial Setup

Clone the repository:

```bash
git clone https://github.com/royallouiss/linux-server-monitoring-system.git

cd linux-server-monitoring-system
```

Install dependencies:

```bash
uv sync
```

---

# Daily Workflow

## 1. Update your local repository

Before starting work:

```bash
git checkout main
git pull origin main
```

---

## 2. Create a feature branch

Example:

```bash
git checkout -b feature/servers
```

Now all your work belongs to this feature.

---

## 3. Work on your assigned task

Example:

- Create models
- Create views
- Create templates
- Test the feature

---

## 4. Check modified files

```bash
git status
```

---

## 5. Stage changes

```bash
git add .
```

or

```bash
git add filename.py
```

---

## 6. Commit changes

Use meaningful commit messages.

Good examples:

```bash
git commit -m "Add Server model"

git commit -m "Create server registration form"

git commit -m "Implement SSH connection service"
```

Avoid:

```
update

changes

final

latest
```

---

## 7. Push your branch

```bash
git push -u origin feature/servers
```

---

## 8. Merge

The Team Lead reviews the feature.

If everything is correct:

```
feature/servers
        │
        ▼
      Merge
        │
        ▼
       main
```

---

# Updating Your Branch

If someone else has merged new work into `main`:

```bash
git checkout main

git pull origin main

git checkout feature/servers

git merge main
```

Resolve conflicts if Git asks.

---

# Important Rules

✅ Pull before starting work.

✅ Commit small changes frequently.

✅ Push your branch regularly.

✅ Test before committing.

✅ Write meaningful commit messages.

❌ Never work directly on `main`.

❌ Never commit `.env`.

❌ Never commit `.venv`.

❌ Never delete another developer's branch.

---

# Team Responsibilities

## Team Lead

- Maintains the repository
- Reviews features
- Merges completed work
- Keeps `main` stable

---

## Developers

- Work on assigned feature branches
- Test their code
- Commit meaningful changes
- Push their branches

---

# Git Commands Cheat Sheet

Clone repository

```bash
git clone <repository-url>
```

Check status

```bash
git status
```

Create branch

```bash
git checkout -b feature/name
```

Switch branch

```bash
git checkout main
```

Pull latest changes

```bash
git pull origin main
```

Stage files

```bash
git add .
```

Commit

```bash
git commit -m "Your message"
```

Push

```bash
git push
```

# Team Module Assignment

| Team Member | Branch | Module |
|-------------|--------|--------|
| Royal (Team Lead) | feature/servers | Server Management & Project Integration |
| Member 2 | feature/dashboard | Dashboard |
| Member 3 | feature/monitoring | Monitoring |
| Member 4 | feature/reports | Reports |
| Member 5 | feature/alerts | Alerts |

Each member is responsible for their assigned module.

Do not modify another member's module without discussing it first.

All completed work must be committed and pushed to the corresponding feature branch.



