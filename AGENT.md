Taunggyi City Church — Agent Guide
Project Overview
Taunggyi City Church is a Django-based backend project.

The project is being developed to support church operations, including user management, authentication, attendees, and related church-management functionality.

The repository is maintained on GitHub:

https://github.com/ANG-KUNG-TANG/Taunggyi-City-Church
Current Development Status
Completed: Backend Restructuring
The Django backend has been moved into the backend/ directory.

The restructuring was committed and pushed to GitHub.

Commit:
9a6b59e chore: move Django backend into backend directory
Completed: Remote Workflow Integration
The existing GitHub Actions workflow was integrated into the local branch.

Remote commit:
e3de647 Add GitHub Actions workflow for Python package

The merge was completed successfully.

Merge commit:
a76025f Merge remote-tracking branch 'origin/main'
Completed: Django Validation
The Django system check was executed from the backend directory:
cd backend
python manage.py check
Result:
System check identified no issues (0 silenced).
Completed: GitHub Push
The merged changes were successfully pushed to:

origin/main

No force push was used.
Project Structure
The Django backend is located in:
backend/
The Django management entry point is:
backend/manage.py
The backend contains Django applications, API modules, configuration, middleware, serializers, models, and supporting services.

The project also contains:
.github/workflows/python-package.yml
This workflow currently defines Python linting and pytest execution.
Development Environment
The project has been developed locally on macOS using a Python virtual environment.

Activate the existing virtual environment from the project root:
source .venv/bin/activate
Enter the backend:
cd backend
Run Django system checks:
python manage.py check
Git Workflow
The primary branch is:
main
The remote is:
origin
Before making changes:
git status -sb
git log -5 --oneline
After implementation:
1. Review the changed files.
2. Run relevant Django checks and tests.
3. Inspect the Git diff.
4. Commit the implementation.
5. Push to GitHub.
Never use force push or destructive Git commands without explicit approval.

Do not discard existing user changes.
Agent Instructions
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
Next Development Priority
The next implementation should review and improve the GitHub Actions workflow after the backend relocation.

The workflow should correctly:
- Install dependencies from the backend directory.
- Run linting against the Django backend.
- Execute the project's actual test suite.
- Use Python versions compatible with the project's dependencies.
- Fail clearly when tests or lint checks fail.
After CI is verified, continue with backend documentation and the next requested church-management feature.
Current Milestone
The backend restructuring is complete and pushed.

The next milestone is to make automated validation reliable and continue implementing church-management functionality without disrupting the existing backend.
Current Development Progress — 2026-11-05
Django Initializer Review
The project initializer is being reviewed in project_init.py.
Changes made
- Updated the virtual environment location to backend/.venv.
- Updated the requirements file location to backend/requirements.txt.
- Changed dependency handling from installation to verification.
- Preserved existing virtual environments and configuration files.
- Added Django system checks before database migrations.
- Made static file collection require interactive confirmation.
- Improved error handling for Django setup commands.
- Updated the initializer description and documentation.
Current Validation
- git diff --check passed.
- python -m py_compile project_init.py passed.
- Django system checks passed previously.
- Static file discovery was verified previously.
Review Status
- backend/config/settings/base.py changes reviewed; static directory formatting is equivalent.
- management.md documents the current progress and remaining work.
- The initializer has not been fully reviewed or runtime-tested.
- Dependency verification still requires further review.
- Database migration behavior requires further safety review.
Current Git Changes
- Modified: project_init.py
- Modified: backend/config/settings/base.py
- Added: management.md
Review the complete diff before staging or committing.
Safety Requirements
- Do not run the initializer without explicit approval.
- Do not run database migrations or static collection during review.
- Do not install or upgrade dependencies automatically.
- Do not delete or recreate the existing virtual environment.
- Preserve existing user changes and environment files.
- Do not commit until the remaining review and validation are complete.
Next Steps
1. Review the initializer for safety and correctness.
2. Review dependency validation against backend/requirements.txt.
3. Review environment-file and VS Code configuration behavior.
4. Verify migration and static collection behavior without executing destructive operations.
5. Review all changed files.
6. Run appropriate non-destructive validation.
7. Commit only after the user approves the final changes.
Phase 1 Completion and Phase 2 Handoff — 2026-11-06
Phase 1: System Design Baseline
Phase 1 is complete. The system design documentation was established, reviewed for consistency, and committed.

The design documents are under backend/docs/:
- architecture.md
- domain_model.md
- database_design.md
- role_permissions.md
- finance_workflow.md
- audit_policy.md
- open_decisions.md
Baseline commit:
b0af822 docs: establish system design baseline

Branch:
feature/phase-1-system-design
CI Test Discovery Fix
The backend GitHub Actions test path was corrected from the invalid apps/users/tests/ path to the existing apps/accounts/tests/ path.

Commit:
015c218 fix: correct backend test discovery path

The commit was pushed to:
origin/feature/phase-1-system-design

The account test module was run locally:
cd backend
python -m pytest apps/accounts/tests/ -v
Result recorded:
8 passed

Important: this confirms the account tests only. Do not claim the complete domain test suite or full project test coverage has passed unless it is subsequently run and verified.
Current Git State (Last Reported)
- Branch: feature/phase-1-system-design
- HEAD: 015c218
- Local branch and origin branch were reported aligned.
- .env.example remains modified locally and uncommitted.
- Review .env.example database settings before staging or committing it.
- Preserve this user change; do not discard or include it in unrelated commits.
Phase 2: Backend Implementation
Phase 2 has been planned but implementation has not yet been confirmed as started.

Recommended first task:
1. Inspect current Django app configuration and model imports.
2. Confirm which domain models are registered with Django.
3. Review existing migrations and migration state.
4. Review PostgreSQL environment configuration without changing .env.example blindly.
5. Identify missing app configs, model registrations, and migration coverage.
6. Implement incrementally according to the approved Phase 1 design.
7. Add and run tests for each domain module.
8. Report only checks and tests that were actually executed.
Potential domain implementation sequence:
- Backend foundation and app/model registration
- Accounts, roles, and permissions
- Zones and members
- Attendance
- Finance and authorization workflow
- Activities and announcements
- Reports and audit
- Integration testing
Phase 2 Safety and Workflow Notes
- Inspect existing code before editing; avoid duplicate models or endpoints.
- Follow the approved design docs in backend/docs/.
- Keep changes focused and incremental.
- Preserve .env.example and all other existing user changes.
- Do not run migrations, static collection, or project initialization without explicit approval when those operations are relevant.
- Run appropriate checks and tests before committing.
- Do not claim full test coverage based only on the 8 account tests.
- Keep commits focused; do not include the unrelated .env.example change in the CI workflow fix.