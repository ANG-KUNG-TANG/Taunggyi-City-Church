Taunggyi City Church — Agent Guide
1. Project Overview
Taunggyi City Church is a church community management system developed as a web application.

The project supports church operations, including:
- Staff accounts and authentication
- Role-based access control
- Member and zone management
- Attendance management
- Activities and announcements
- Donation and fund management
- Financial reporting and audit records
The repository is maintained on GitHub:

https://github.com/ANG-KUNG-TANG/Taunggyi-City-Church
Technology Baseline
- Backend: Django
- API: Django REST Framework
- Database: PostgreSQL
- Frontend: React and TypeScript
- Architecture: Modular monolith
- Version control: Git and GitHub
- CI: GitHub Actions
The approved OOAD and System Design Specification is the primary source of truth for business requirements and architecture.

Do not invent business rules when the design identifies a decision as unresolved.
2. Current Development Status
Completed: Backend Restructuring
The Django backend was moved into:

backend/

The restructuring was committed and pushed.

Commit:

9a6b59e chore: move Django backend into backend directory
Completed: Remote Workflow Integration
The existing GitHub Actions workflow was integrated into the local branch.

Remote commit:

e3de647 Add GitHub Actions workflow for Python package

Merge commit:

a76025f Merge remote-tracking branch 'origin/main'

The merge was completed successfully and pushed without force-pushing.
Completed: Phase 1 — System Design Baseline
Phase 1 established the system design documentation and implementation baseline.

The design documents are located in:

backend/docs/

Documents:
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

The consolidated OOAD and System Design Specification is also available as the project's approved design reference.
Completed: CI Test Discovery Correction
The backend test path in GitHub Actions was corrected from the invalid:

apps/users/tests/

to:

apps/accounts/tests/

Commit:

015c218 fix: correct backend test discovery path

The account test module was previously executed with 8 passing tests. This historical result has since been superseded by the latest Phase 2A test run.
3. Phase 2 — Backend Implementation
Phase 2 implementation is underway.

The first implementation milestone is the backend foundation, particularly staff accounts and role-based access control.
Phase 2A: Accounts and RBAC Foundation
Implementation status: Merged into main through PR #7 on 2026-11-08.
Custom User Model
A custom User model has been implemented with:
- UUID primary key
- Unique email address
- Optional first name and last name
- Active status
- Creation timestamp
- Inherited password hashing and last-login functionality from Django's AbstractBaseUser
The model uses email as its authentication identifier.

The configured model reference is:

AUTH_USER_MODEL = "tcc.User"

The database table is:

users
Custom User Manager
A custom UserManager has been implemented.

It provides:
- Email validation
- Email normalization
- Password hashing through Django's password utilities
- Unusable passwords when no password is supplied
Django superuser creation is explicitly unsupported because the application uses its own documented RBAC architecture.
Role Model
A Role model has been implemented with:
- UUID primary key
- Unique role code
- Role name
- Optional description
- System-role indicator
UserRole Model
A UserRole model represents staff role assignments.

It includes:
- UUID primary key
- User foreign key
- Role foreign key
- Optional assigning user
- Assignment timestamp
- Optional revocation timestamp
The model supports recording role assignment history.
Initial System Roles
The following system roles have been seeded through a data migration:
Role Code	Role Name
ZONE_LEADER	Zone Leader
PASTOR	Pastor
ADMINISTRATOR	Administrator


PUBLIC is not seeded as a database role because Public Visitor is an unauthenticated actor, not an authenticated staff account.
Django Admin and Superuser Decisions
Django Admin integration has been removed from the project configuration.

The application Administrator role is distinct from Django's built-in administrative and superuser concepts.

The custom User model does not inherit PermissionsMixin, and Django superuser creation is not supported.

Do not restore Django Admin, Django superuser functionality, or Django's built-in staff permission model without an explicit architectural reason and approval.
Migration Status
The following migrations have been created and applied to the local PostgreSQL database:
- 0002_rebuild_user_and_add_rbac.py
  - Rebuilds the legacy User table.
  - Creates the UUID-based User model.
  - Creates Role and UserRole tables.
- 0003_seed_system_roles.py
  - Seeds the three initial system roles.
The original migration 0001_initial.py remains unchanged.

The local migration state was verified:
- 0001_initial: applied
- 0002_rebuild_user_and_add_rbac: applied
- 0003_seed_system_roles: applied
The legacy test User record was removed as part of the approved table rebuild. A database backup was created before the rebuild.

Backup location:

/Users/anrikung/taunggyi_church_before_user_rebuild.dump

This is a local backup and must not be committed or shared publicly.
Phase 2A Validation
The following results have been recorded:
Validation	Result
Accounts tests	9 passed
Django system check	Passed
Migration consistency check	No changes detected
Flake8 critical-error checks	0 errors
git diff --check	Passed
Black formatting	Formatting executed; final --check still needs verification


The accounts test command was:
python -m pytest apps/accounts/tests/ -v
The migration consistency command was:
python manage.py makemigrations --check --dry-run
Do not describe these results as full project test coverage. Only the accounts test module has been verified.
4. Current Git State
Verified Remote Status — 2026-11-08
Phase 2A has been committed, pushed, and merged into main.
- PR: https://github.com/ANG-KUNG-TANG/Taunggyi-City-Church/pull/7
- PR title: feat(accounts): establish custom user and RBAC foundation
- Feature branch: feat/phase-2a-accounts-roles
- Feature commit: 060c9299f7edc6bb267b62b2ecbcd6f31cb8eee9
- Merge commit on main: f29c265788b0c72d59c38c4a26de3d3f2af6a748
- PR status: merged
- Base branch: main
The merge was verified against GitHub. The main branch points to the merge commit above, and PR #7 reports merged=true.
Local Working Tree
The local working-tree state has not been inspected as part of this update. Preserve any local staged, unstaged, or untracked changes. Do not assume the local feature branch is synchronized with main until git status, git branch -vv, and the latest remote refs have been checked.
Environment Configuration Note
The earlier .env.example review identified a possible PostgreSQL port inconsistency:
DATABASE_URL=postgresql://user:password@db:3306/church_operation
DB_PORT=5432
This remains a review note, not a confirmed defect. Verify how the project loads these settings before changing them. Never commit actual secrets or local credentials.
Git Actions
Phase 2A does not need another commit or PR: it is already merged into main.

For any subsequent work:
1. Inspect git status -sb and recent commits.
2. Confirm the current branch and its upstream.
3. Preserve all existing local changes.
4. Review the complete diff and run relevant checks.
5. Commit and push only the intended changes.
6. Verify the remote branch and CI result after pushing.
Never use force push or destructive Git commands without explicit approval.
5. Development Environment
The project is developed locally on macOS using a Python virtual environment.

Activate the existing virtual environment from the repository root:
source .venv/bin/activate
Enter the backend directory:
cd backend
Run Django system checks:
python manage.py check
Run account tests:
python -m pytest apps/accounts/tests/ -v
Check migration consistency:
python manage.py makemigrations --check --dry-run
Check formatting:
python -m black --check .
Run the configured critical Flake8 checks:
python -m flake8 apps/ \
  --count \
  --select=E9,F63,F7,F82 \
  --show-source \
  --statistics
Do not assume a command has passed unless its actual output has been observed.
6. Architecture and Business Rules
The OOAD System Design Specification governs implementation decisions.
Release 1 Roles
The documented actors and roles are:
- Public Visitor
- Zone Leader
- Pastor
- Administrator
Role Boundaries
Public Visitor
- Unauthenticated.
- Can access published public information.
- Does not require a staff account.
Zone Leader
- Manages members and attendance within assigned zones.
- Must not access records outside assigned zones.
- Must not transfer members between zones unless the approved requirements explicitly permit it.
Pastor
- Has church-wide member, zone, and attendance capabilities.
- Has publishing and financial capabilities.
Administrator
- Manages staff accounts, roles, and system configuration.
- Has publishing, audit-review, and explicitly defined financial capabilities.
- Does not automatically have access to member records.
Authentication and Authorization
- Staff login accounts must remain separate from church Member profiles.
- Members do not receive login accounts in Release 1.
- Authorization must be enforced on the backend.
- Apply deny-by-default permission handling.
- Zone Leaders require zone-scoped object-level authorization.
- Frontend visibility is not a security boundary.
Finance
- Finance access is restricted to Pastor and Administrator.
- Financial records use the documented Pending, Authorised, and Rejected workflow.
- Authorised financial records must not be silently overwritten.
- Corrections and reversals must preserve the original financial history.
- Sensitive financial operations require attributable audit records.
Database
- UUID primary keys are the proposed standard for core entities.
- Use database constraints and transactions to preserve integrity.
- Do not introduce destructive deletion policies without reviewing the design and obtaining approval.
7. Unresolved Design Decisions
Do not silently turn proposed policies into confirmed business rules.

The following decisions remain unresolved or require explicit confirmation before implementation:
- Whether a staff user may hold multiple active roles simultaneously.
- Whether a staff user may have multiple active Zone Leader assignments.
- The exact active-role semantics and primary-role policy.
- The authentication approach: secure cookie sessions or token authentication.
- The church-wide attendance operating workflow.
- Financial self-authorisation and separation-of-duties policy.
- Audit retention policy.
- Currency and timezone policy.
- Other open decisions documented in backend/docs/open_decisions.md and the OOAD specification.
When an implementation depends on an unresolved decision:
1. Identify the relevant decision.
2. Explain the technical impact.
3. Ask for confirmation when necessary.
4. Avoid inventing a permanent business rule.
8. Project Structure
The Django backend is located in:

backend/

The Django management entry point is:

backend/manage.py

Important backend directories include:
- backend/apps/
- backend/config/
- backend/requirements/
- backend/docs/
The accounts implementation is located in:

backend/apps/accounts/

The TCC model registration and migrations are located in:

backend/apps/tcc/

Follow the existing app-label and model-registration architecture. Do not move models between Django apps or change migration ownership without reviewing the consequences.
9. Git Workflow
The primary branch is:

main

The remote is:

origin

Before making changes:
git status -sb
git log -5 --oneline
Before committing:
1. Review all modified and newly created files.
2. Run relevant checks and tests.
3. Inspect the complete Git diff.
4. Check for secrets and accidental environment changes.
5. Confirm the staged files.
After implementation:
1. Commit with a clear, focused message.
2. Push to the appropriate feature branch.
3. Open a pull request against the intended base branch.
4. Review CI results before merging.
Never use force push or destructive Git commands without explicit approval.

Do not discard existing user changes.

Do not assume that pushing a branch publishes uncommitted or staged changes.
10. Agent Instructions
When continuing development:
1. Inspect the existing implementation before modifying files.
2. Follow the approved OOAD specification and backend/docs/.
3. Follow existing Django architecture and naming conventions.
4. Avoid creating duplicate models, serializers, services, or API endpoints.
5. Keep changes focused on the requested feature.
6. Do not introduce unnecessary dependencies.
7. Do not hardcode secrets or credentials.
8. Preserve existing functionality.
9. Validate changes before committing.
10. Explain important implementation decisions.
11. Work incrementally.
12. Report actual command results.
13. Distinguish implemented work from proposed or planned work.
14. Preserve staged, unstaged, and untracked user changes.
15. Do not claim that a feature, test, migration, or deployment succeeded unless it has been verified.
Database Safety
- Inspect migration state before proposing migration changes.
- Do not drop databases or tables without explicit approval.
- Do not reverse or rewrite applied migrations casually.
- Review generated SQL for significant schema changes.
- Preserve backups and never commit local database backups.
- Do not run destructive database operations during code review.
Initializer Safety
The project initializer project_init.py was previously under review.

Its review included:
- Virtual environment location.
- Requirements file location.
- Dependency verification.
- Django system checks.
- Static collection confirmation.
- Migration behavior.
- Environment-file handling.
- VS Code configuration.
The initializer was not confirmed as fully reviewed or runtime-tested.

Do not execute the initializer, run migrations, collect static files, install dependencies, or recreate the virtual environment without the relevant approval.
11. Next Development Priorities
Immediate: Begin Phase 2B — Permissions and Authorization
Phase 2A has been merged into main through PR #7. The next implementation milestone is Phase 2B, subject to the approved OOAD and unresolved design decisions.
1. Review the OOAD permission matrix and backend/docs/role_permissions.md.
2. Define backend permission classes and authorization services.
3. Implement server-side role checks with deny-by-default behavior.
4. Establish zone-scoped object authorization for Zone Leaders.
5. Add tests for both permitted and denied operations.
6. Confirm unresolved role-multiplicity policies before enforcing them.
Do not assume that creating Role and UserRole models alone completes RBAC. Authorization enforcement is a separate implementation task. Do not begin the authentication redesign without first resolving the authentication approach recorded in backend/docs/open_decisions.md.
Subsequent Domain Implementation
Recommended sequence:
1. Zones and Members
2. Attendance
3. Finance and authorization workflow
4. Activities and announcements
5. Reports and audit
6. Integration testing
Adjust this sequence only when dependencies or approved project priorities justify doing so.
12. Current Milestone Summary
Phase 1 — System Design Baseline: Completed.

Phase 2A — Custom Accounts and RBAC Data Foundation: Implemented, validated according to the recorded accounts-focused checks, and merged into main through PR #7 on 2026-11-08. Merge commit: f29c265788b0c72d59c38c4a26de3d3f2af6a748.

Phase 2B — Backend Authorization Enforcement: Not yet confirmed as implemented. This is the next development milestone.

Remaining Release 1 Domains: Not yet confirmed as implemented.

The immediate priority is to begin Phase 2B after inspecting the current local Git state and reviewing the approved permission design. Preserve local changes and report only validation that has actually been run.