# Taunggyi City Church — Agent Guide

## Project Overview

Taunggyi City Church is a Django-based backend project.

The project is being developed to support church operations, including user management, authentication, attendees, and related church-management functionality.

The repository is maintained on GitHub:

https://github.com/ANG-KUNG-TANG/Taunggyi-City-Church

## Current Development Status

### Completed: Backend Restructuring

The Django backend has been moved into the `backend/` directory.

The restructuring was committed and pushed to GitHub.

Commit:
`9a6b59e chore: move Django backend into backend directory`

### Completed: Remote Workflow Integration

The existing GitHub Actions workflow was integrated into the local branch.

Remote commit:
`e3de647 Add GitHub Actions workflow for Python package`

The merge was completed successfully.

Merge commit:
`a76025f Merge remote-tracking branch 'origin/main'`

### Completed: Django Validation

The Django system check was executed from the backend directory:

```bash
cd backend
python manage.py check
```

Result:

```text
System check identified no issues (0 silenced).
```

### Completed: GitHub Push

The merged changes were successfully pushed to:

`origin/main`

No force push was used.

## Project Structure

The Django backend is located in:

```text
backend/
```

The Django management entry point is:

```text
backend/manage.py
```

The backend contains Django applications, API modules, configuration, middleware, serializers, models, and supporting services.

The project also contains:

```text
.github/workflows/python-package.yml
```

This workflow currently defines Python linting and pytest execution.

## Development Environment

The project has been developed locally on macOS using a Python virtual environment.

Activate the existing virtual environment from the project root:

```bash
source .venv/bin/activate
```

Enter the backend:

```bash
cd backend
```

Run Django system checks:

```bash
python manage.py check
```

## Git Workflow

The primary branch is:

```text
main
```

The remote is:

```text
origin
```

Before making changes:

```bash
git status -sb
git log -5 --oneline
```

After implementation:

1. Review the changed files.
2. Run relevant Django checks and tests.
3. Inspect the Git diff.
4. Commit the implementation.
5. Push to GitHub.

Never use force push or destructive Git commands without explicit approval.

Do not discard existing user changes.

## Agent Instructions

When continuing development:

1. Inspect the existing implementation before modifying files.
2. Follow the existing Django architecture and naming conventions.
3. Avoid creating duplicate models, serializers, services, or API endpoints.
4. Keep changes focused on the requested feature.
5. Do not introduce unnecessary dependencies.
6. Do not hardcode secrets or credentials.
7. Preserve existing functionality.
8. Validate changes before committing.
9. Explain important implementation decisions.
10. Work incrementally and report the actual results of commands.

Do not claim that a feature, test, or deployment succeeded unless it has been verified.

## Next Development Priority

The next implementation should review and improve the GitHub Actions workflow after the backend relocation.

The workflow should correctly:

- Install dependencies from the backend directory.
- Run linting against the Django backend.
- Execute the project's actual test suite.
- Use Python versions compatible with the project's dependencies.
- Fail clearly when tests or lint checks fail.

After CI is verified, continue with backend documentation and the next requested church-management feature.

## Current Milestone

The backend restructuring is complete and pushed.

The next milestone is to make automated validation reliable and continue implementing church-management functionality without disrupting the existing backend.
