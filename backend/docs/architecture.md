# Taunggyi City Church Community Management System
## System Architecture

**Document:** System Architecture
**Version:** 1.0
**Status:** Proposed Release 1 design
**Last updated:** 6 November 2026

---

## 1. Purpose

This document defines the proposed architecture of the Taunggyi City Church Community Management System.

It establishes the system components, architectural responsibilities, module boundaries, request flow, security principles, and technical constraints for Release 1.

The architecture is intended to support a maintainable church management application while preserving the approved business rules and access restrictions.

This document describes the intended design. It does not claim that every component has already been implemented or deployed.

## 2. System Overview

The Taunggyi City Church Community Management System is a web application that provides public church information and protected management functions for authorised staff.

The system supports:

- Public church information.
- Member and zone management.
- Staff account administration.
- Attendance sessions and attendance records.
- Aggregate visitor counts.
- Activities and announcements.
- Donation and fund management.
- Operational and financial reporting.
- Audit history.

The application uses a separately built frontend and a Django REST Framework backend.

PostgreSQL is the primary transactional database.

Release 1 follows a modular monolith architecture. Domain modules are logically separated but operate within one backend application and share the same database.

## 3. Architecture Decisions

| ID | Decision |
|---|---|
| ADR-001 | Use React and TypeScript for the frontend. |
| ADR-002 | Use Django and Django REST Framework for the backend. |
| ADR-003 | Use PostgreSQL as the transactional database. |
| ADR-004 | Use a modular monolith for Release 1. |
| ADR-005 | Enforce authorization in the backend. |
| ADR-006 | Apply zone-based restrictions to Zone Leader operations. |
| ADR-007 | Restrict financial operations and reports to Pastor and Administrator. |
| ADR-008 | Maintain an attributable audit history for sensitive operations. |
| ADR-009 | Use database constraints and transactions to protect data integrity. |
| ADR-010 | Defer distributed infrastructure unless a demonstrated requirement justifies it. |

These decisions establish the proposed Release 1 architecture. Details that remain unresolved are recorded in `open_decisions.md`.

## 4. Architectural Style

### 4.1 Modular Monolith

The backend will be implemented as a modular monolith.

Each domain module owns its models, business rules, application services, and API interfaces.

Modules share the Django application runtime and PostgreSQL database, but they must not bypass one another's business rules or authorization policies.

The modular monolith is selected because Release 1 is designed for one church organisation and does not require distributed infrastructure.

### 4.2 Architectural Layers

The backend follows these logical layers:

1. API and view layer.
2. Serializer and validation layer.
3. Permission and policy layer.
4. Application service layer.
5. Domain model layer.
6. Repository and query layer.
7. PostgreSQL persistence layer.
8. Audit service.

Responsibilities must remain separated.

API views must not independently implement complex business workflows that belong in application services.

Database access must respect the domain module's rules and the requesting actor's permissions.

## 5. System Components

### 5.1 Frontend

**Technology:** React and TypeScript.

Responsibilities:

- Render the public church website.
- Render the staff management dashboard.
- Display information according to the authenticated user's role.
- Submit requests to the backend API.
- Display validation errors and operation results.
- Provide forms for member, attendance, content, and authorised financial operations.
- Present permitted reports.

The frontend may hide actions that the user cannot perform.

However, frontend visibility is not an authorization mechanism. The backend must independently enforce every permission.

### 5.2 Backend API

**Technology:** Django REST Framework.

Responsibilities:

- Receive HTTP requests.
- Authenticate staff requests.
- Validate request data.
- Enforce role and object-level permissions.
- Apply business rules.
- Coordinate domain services.
- Read and write transactional records.
- Record audit events for sensitive operations.
- Return appropriate HTTP responses.

The API will use versioned routes.

The proposed API prefix is:

`/api/v1/`

The final route structure must be documented in `api_conventions.md`.

### 5.3 Authentication and Authorization

The authentication and authorization component is responsible for identifying staff users and enforcing access restrictions.

It must support:

- Staff authentication.
- Role-based authorization.
- Zone-scoped authorization.
- Financial access restrictions.
- Object-level permission checks.
- Staff account deactivation.

Authorization must follow the principle of least privilege.

A valid login does not automatically grant permission to access every system function.

### 5.4 PostgreSQL

PostgreSQL is the primary transactional database.

Responsibilities:

- Store application records.
- Enforce foreign-key relationships.
- Enforce uniqueness and integrity constraints.
- Support transactional operations.
- Support reporting queries.
- Preserve financial and audit history.

The database must not rely exclusively on frontend validation to protect data integrity.

### 5.5 Media Storage

Media storage supports files associated with public content, such as activity or announcement images.

Responsibilities:

- Store uploaded media.
- Provide controlled access to files.
- Validate uploaded file types and sizes.
- Prevent unauthorised file access.
- Support the frontend's permitted media requests.

The production storage provider and retention policy must be confirmed before deployment.

## 6. Domain Modules

### 6.1 Accounts

Responsibilities:

- Staff identity.
- Authentication.
- Staff status.
- Role assignment.
- Account administration.
- Authentication-related permissions.

The accounts module represents staff login identities.

Church member profiles are maintained separately.

### 6.2 Members

Responsibilities:

- Member profiles.
- Member creation and editing.
- Member lifecycle.
- Current zone association.
- Member-related validation.

Each member must have one current zone.

Zone Leaders must not be able to transfer members between zones.

### 6.3 Zones

Responsibilities:

- Zone records.
- Zone Leader assignments.
- Zone-related validation.
- Zone access policies.

Zone assignment and transfer operations must enforce the approved permissions.

### 6.4 Attendance

Responsibilities:

- Attendance sessions.
- Present and Absent records.
- Member attendance.
- Aggregate visitor counts.
- Attendance validation.
- Attendance reporting.

Attendance operations must enforce duplicate prevention and session-state rules.

Visitors must be represented through aggregate counts rather than individual visitor profiles.

### 6.5 Content

Responsibilities:

- Activities.
- Announcements.
- Publication state.
- Public content management.

Only authorised staff may create or publish protected content.

Public users may access published content according to the public access rules.

### 6.6 Finance

Responsibilities:

- Donation records.
- Fund records.
- Financial categories.
- Financial authorisation.
- Financial decisions.
- Adjustments.
- Corrections and reversals.
- Financial history.

Financial access is restricted to Pastor and Administrator.

Financial records must follow the approved authorisation workflow.

Authorised financial records must not be silently modified in place.

Corrections must preserve the original record and provide an attributable history.

### 6.7 Reports

Responsibilities:

- Attendance reports.
- Member reports.
- Operational reports.
- Financial reports.
- Report filtering.
- Report-level authorization.

Reports must use the same authorization boundaries as the underlying records.

Zone Leaders must not access information outside their assigned zone.

Financial reports are restricted to Pastor and Administrator.

### 6.8 Audit

Responsibilities:

- Record sensitive actions.
- Record relevant actors.
- Record timestamps.
- Preserve financial decisions.
- Support protected audit queries.

Audit records must not be editable or deletable through ordinary application operations.

Sensitive operations must record their audit events within the appropriate transaction boundary.

## 7. Request Flow

The proposed request flow is:

1. A user opens the application in a browser.
2. DNS resolves the application domain.
3. Web hosting serves the frontend over HTTPS.
4. The frontend sends a request to the versioned backend API.
5. The backend identifies the requesting user, where authentication is required.
6. The permission layer checks role, zone scope, financial access, and object permissions.
7. The relevant domain module validates the request.
8. The application service coordinates the business operation.
9. PostgreSQL performs the required transactional reads and writes.
10. Sensitive operations record their audit events.
11. The backend returns the permitted response.
12. The frontend displays the result.

Unauthorised requests must be rejected by the backend.

## 8. Authorization Boundaries

### 8.1 Public Users

Public users may access public information that is approved for publication.

Public access must not expose protected staff, member, attendance, financial, or audit information.

### 8.2 Zone Leader

Zone Leaders operate within their assigned zone.

Their permissions must be restricted to approved zone-specific operations.

They must not:

- Access members outside their assigned zone.
- Transfer members between zones.
- Access financial management functions.
- Access unrestricted church-wide operational reports.

### 8.3 Pastor

Pastor has church-wide operational responsibilities.

The Pastor's approved responsibilities include member and zone management, attendance management, and permitted church-wide reporting.

Pastor also has financial permissions.

### 8.4 Administrator

Administrator responsibilities include staff account administration, role management, system configuration, publication, and audit review.

Administrator also has the explicitly approved financial permissions.

Administrator access to member data must not be assumed merely because the account has administrative responsibilities.

Every protected operation must use an explicit permission policy.

## 9. Module Interaction Rules

The following rules apply to module interactions:

1. A module must not bypass another module's domain service to mutate its data.
2. Shared database access does not imply shared authorization.
3. Each domain operation must validate the requesting actor.
4. Finance endpoints must require explicit financial permissions.
5. Reports must use approved query services.
6. Financial reports must use authorised-only calculations.
7. Sensitive operations must record audit events.
8. Database constraints must protect relational integrity.
9. Cross-module operations must use clear service boundaries.
10. Module dependencies must remain explicit and maintainable.

## 10. Transaction Boundaries

### 10.1 Member Operations

Member creation or editing and its associated audit event must commit atomically.

If the operation fails, the transaction must not leave a partially completed member change.

### 10.2 Attendance Operations

Attendance changes and visitor-count updates must commit with their associated audit events in the same transaction.

### 10.3 Financial Authorisation

Financial authorisation must:

- Lock the target record where necessary.
- Validate its current state.
- Apply the authorisation decision.
- Record the audit event.
- Commit the changes atomically.

### 10.4 Financial Corrections

Financial corrections and reversals must preserve the original record.

Correction creation and correction authorisation must use separate transactions.

The complete financial history must remain attributable.

## 11. Database Design Principles

The database design must follow these principles:

- Use database-enforced foreign keys.
- Use unique constraints where required.
- Use database constraints for important integrity rules.
- Use transactions for related operations.
- Use UUID primary keys for core entities, as proposed.
- Use timezone-aware timestamps.
- Use decimal numeric types for monetary values.
- Index foreign keys and common report filters.
- Preserve audit history.
- Minimise sensitive personal data.
- Apply controlled deletion or deactivation policies.

The detailed entity relationships and constraints belong in `database_design.md`.

## 12. Security Principles

The system must apply:

- Least-privilege authorization.
- Backend permission enforcement.
- HTTPS for application traffic.
- Secure password hashing.
- Input validation.
- Safe database access.
- CSRF protection where applicable.
- Appropriate CORS configuration.
- Protected file access.
- Restricted production configuration.
- Secure secret management.
- Audit logging for sensitive operations.
- Restricted backups.

Production deployment must not expose development secrets or use unsafe debug settings.

The final authentication approach and session/token configuration must be documented before production deployment.

### 12.1 Centralised Error and Exception Handling

**Status:** Proposed
**Target Release:** Release 1
**Priority:** High
**Architecture Type:** Backend Cross-Cutting Concern

#### 12.1.1 Purpose

The Taunggyi City Church Community Management System shall implement a centralised error and exception-handling architecture to ensure consistent, secure, and predictable error behaviour across all backend applications.

The architecture shall separate business-level failure identification, API error response formatting, and error logging.

Each application shall remain responsible for identifying its own business and domain failures. The central exception handler shall provide a consistent API response format, while the logging component shall record relevant diagnostic information.

The architecture shall support the following applications:

- Accounts
- Zones
- Members
- Attendance
- Finance
- Reports
- Other future backend applications

The exception-handling architecture shall be implemented incrementally without requiring all applications to adopt it simultaneously.

#### 12.1.2 Architectural Principles

**1. Domain-Specific Exceptions**

Each application shall define domain exceptions for business failures that require explicit handling.

Examples include:

- Invalid role assignment
- Zone not found
- Inactive zone
- Invalid Zone Leader assignment
- Member not found
- Invalid member transfer
- Attendance session closed
- Duplicate attendance
- Financial record conflict
- Financial authorization failure

Domain exceptions shall describe business failures rather than implementation failures.

**2. Preserve Built-In Exceptions**

The system shall continue to use appropriate Python, Django, and Django REST Framework exceptions.

Examples include:

- ValueError
- TypeError
- ValidationError
- PermissionDenied
- AuthenticationFailed
- NotFound
- APIException

The architecture shall not require every exception to be converted into a custom domain exception.

Custom exceptions shall be introduced only when they provide meaningful domain-specific information or support consistent API handling.

**3. Centralised API Error Formatting**

All API errors shall use a consistent response structure.

The central exception handler shall:

- Identify the exception type.
- Determine the appropriate HTTP status code.
- Return a stable error code.
- Provide a safe, user-facing message.
- Include relevant validation details when appropriate.
- Include the request ID when available.
- Prevent internal implementation details from being exposed.

The central handler shall preserve the standard behaviour of Django REST Framework exceptions unless the project explicitly defines a different response policy.

**4. Separation of Responsibilities**

The architecture shall maintain the following responsibilities:

| Component | Responsibility |
|---|---|
| Domain services | Identify and raise business-level exceptions |
| Domain exception classes | Represent specific business failures |
| Central exception handler | Convert exceptions into consistent API responses |
| Request-ID middleware | Associate requests with a unique identifier |
| Error logging component | Record diagnostic information |
| Automated tests | Verify exception behaviour and response consistency |

Domain services shall not directly construct HTTP responses.

The central exception handler shall not contain application-specific business logic.

**5. Security and Information Protection**

Error responses shall not disclose:

- Database credentials
- Secret keys
- JWT signing information
- SQL statements
- Internal file paths
- Stack traces
- Sensitive member information
- Private information belonging to another zone
- Financial information that the requesting user is not authorised to access

The system shall follow the existing role-based access-control architecture.

An error response shall not reveal whether a protected member, financial record, or other restricted resource exists when that information is not available to the requesting user.

The system shall follow a deny-by-default policy.

#### 12.1.3 Existing Backend Structure and Integration

The central exception architecture shall be implemented inside the existing backend common package.

Current structure:

backend/
└── common/
    ├── core_validators/
    │   ├── exceptions.py
    │   ├── decorators.py
    │   ├── registry.py
    │   └── rules.py
    ├── exceptions.py
    ├── middleware/
    │   ├── correlation_id.py
    │   └── request_id.py
    ├── jwt/
    ├── utils/
    ├── pagination.py
    ├── permissions.py
    ├── serializers.py
    ├── tasks.py
    └── validators.py

The exception architecture shall extend this existing structure rather than introduce another independent common package.

**Existing Exception Modules**

The existing files shall retain their distinct responsibilities:

- `backend/common/core_validators/exceptions.py` shall remain responsible for exceptions related to the core validation framework.
- The existing `backend/common/exceptions.py` file shall be migrated into the central domain-exception package.
- Domain exceptions shall not be placed inside the core validation framework unless they specifically belong to that framework.

**Migration Requirement**

The existing `backend/common/exceptions.py` file is currently an empty Python module.

Before implementing the proposed package, it shall be converted into a package directory.

The migration shall replace:

`backend/common/exceptions.py`

with:

`backend/common/exceptions/`

The existing empty module shall not remain alongside the package under the same name.

#### 12.1.4 Proposed Package Structure

The proposed exception architecture shall use the following structure:

backend/
└── common/
    ├── exceptions/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── codes.py
    │   ├── accounts.py
    │   ├── zones.py
    │   ├── members.py
    │   ├── attendance.py
    │   └── finance.py
    │
    ├── handlers/
    │   ├── __init__.py
    │   └── exception_handler.py
    │
    ├── logging/
    │   ├── __init__.py
    │   └── error_logger.py
    │
    ├── core_validators/
    │   ├── exceptions.py
    │   ├── decorators.py
    │   ├── registry.py
    │   └── rules.py
    │
    ├── middleware/
    │   ├── correlation_id.py
    │   └── request_id.py
    │
    ├── jwt/
    ├── utils/
    ├── pagination.py
    ├── permissions.py
    ├── serializers.py
    ├── tasks.py
    └── validators.py

**Package Responsibilities**

| File | Responsibility |
|---|---|
| exceptions/base.py | Define the common domain exception base class |
| exceptions/codes.py | Define stable application error codes |
| exceptions/accounts.py | Define account and role-assignment exceptions |
| exceptions/zones.py | Define zone-related exceptions |
| exceptions/members.py | Define member-related exceptions |
| exceptions/attendance.py | Define attendance-related exceptions |
| exceptions/finance.py | Define finance-related exceptions |
| handlers/exception_handler.py | Centralise API exception formatting |
| logging/error_logger.py | Provide structured error logging |

The exception package shall be extended as additional applications are implemented.

The package shall not require every application to create an exception module before domain exceptions are needed.

#### 12.1.5 Domain Exception Design

Domain exceptions shall inherit from a shared base exception.

The base exception shall provide the following information:

- Stable error code
- Safe error message
- Optional structured details
- Appropriate HTTP status code

The base exception shall not contain request-specific data or depend directly on Django REST Framework response objects.

**Proposed Base Exception**

The conceptual structure shall be:

```python
class DomainException(Exception):
    """
    Base class for application-level domain exceptions.
    """

    code = "COMMON_DOMAIN_ERROR"
    message = "A domain operation could not be completed."
    status_code = 400

    def __init__(
        self,
        message=None,
        details=None,
    ):
        self.message = message or self.message
        self.details = details

        super().__init__(self.message)
## 13. Release 1 Infrastructure

Release 1 requires:

- Frontend hosting.
- HTTPS.
- Django REST Framework backend.
- PostgreSQL database.
- Media storage where required.
- Application configuration.
- Database migrations.
- Logging.
- Backup and recovery procedures.

The application must be deployable without introducing unnecessary distributed infrastructure.

The following are not required for Release 1 unless an approved requirement justifies them:

- Microservices.
- Kubernetes.
- Kafka.
- Distributed caching.
- Dedicated analytics warehouse.
- Independent search infrastructure.
- Mandatory background-job infrastructure.

Long-running tasks may use background processing in a future phase if performance evidence demonstrates the need.

## 14. Proposed Project Structure

The backend should maintain clear domain boundaries.

```text
backend/
├── config/
│   ├── settings/
│   ├── urls.py
│   └── ...
├── apps/
│   ├── accounts/
│   ├── members/
│   ├── zones/
│   ├── attendance/
│   ├── content/
│   ├── finance/
│   ├── reports/
│   └── audit/
├── common/
├── docs/
└── manage.py
```

This is the proposed logical structure.

The actual repository structure must be checked before implementation changes are made.

## 15. Non-functional Requirements

The architecture must support:

### Security

Backend authorization, restricted financial access, zone-scoped operations, secure authentication, and protected audit history.

### Integrity

Database constraints, atomic transactions, duplicate prevention, and controlled financial corrections.

### Maintainability

Explicit module boundaries, reusable services, consistent API conventions, and documented business rules.

### Reliability

Controlled error handling, transactional operations, logging, backup procedures, and recovery planning.

### Testability

Unit tests for domain rules, integration tests for database operations, and API tests for authorization.

### Performance

Efficient queries, appropriate indexes, and report queries that respect authorization.

Performance requirements and measurable targets must be defined in the requirements documentation.

## 16. Architecture Limitations and Unresolved Decisions

The architecture does not independently resolve:

- The final authentication and session/token strategy.
- The church display timezone.
- The attendance operating workflow.
- The approved financial categories and fund types.
- The final deployment provider.
- The media storage provider.
- Financial correction and approval details not already confirmed.
- Additional operational or performance targets.

These decisions must be documented in `open_decisions.md`.

The architecture must not silently introduce new business rules to resolve them.

## 17. Architecture Validation

The architecture is considered ready for implementation review when:

- The selected technologies are documented.
- Module responsibilities are defined.
- Module dependencies are explicit.
- Authentication and authorization boundaries are documented.
- Zone restrictions are documented.
- Financial restrictions are documented.
- Transaction boundaries are documented.
- Database design follows the integrity requirements.
- Outstanding decisions are recorded.
- The architecture is consistent with the requirements and domain model.

## 18. Related Documentation

| Document | Relationship |
|---|---|
| `domain_model.md` | Defines domain entities and business relationships. |
| `database_design.md` | Defines tables, fields, constraints, and indexes. |
| `role_permissions.md` | Defines role and object-level authorization. |
| `attendance_workflow.md` | Defines attendance operations and state transitions. |
| `finance_workflow.md` | Defines financial operations and authorisation. |
| `audit_policy.md` | Defines audit events and retention controls. |
| `reporting.md` | Defines report scope and calculations. |
| `api_conventions.md` | Defines API interface conventions. |
| `error_handling.md` | Defines API and application error behavior. |
| `testing_strategy.md` | Defines verification and test coverage. |
| `deployment.md` | Defines deployment and operational requirements. |
| `open_decisions.md` | Tracks unresolved design decisions. |

---

**Document status:** Proposed Release 1 architecture. Review and approval are required before treating it as the final implementation baseline.
