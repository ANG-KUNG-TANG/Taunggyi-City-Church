# Role and Permission Model

## 1. Purpose

This document defines the Release 1 roles and their permissions for
the Taunggyi City Church Community Management System.

All permission checks must be performed on the server.

Role permissions define the operations a user may perform.
Zone-based object permissions further restrict which member and
attendance records a Zone Leader may access.

Deny by default applies to capabilities that are not explicitly
listed or granted.

## 2. Roles

Release 1 defines the following roles:

- Public Visitor
- Zone Leader
- Pastor
- Administrator

## 3. Permission Rules

### 3.1 Public Visitor

Public Visitors may:

- View published public information.

Public Visitors may not access private member records,
attendance records, visitor counts, or financial information.

### 3.2 Zone Leader

Zone Leaders may:

- View member records within their assigned zone.
- Create and edit member records within their assigned zone.
- Create attendance sessions for their assigned zone.
- Record member attendance within their assigned zone.
- Record visitor counts within their assigned zone.
- View attendance reports for their assigned zone.

Zone Leaders may not:

- Transfer members between zones.
- Create church-wide attendance sessions.
- Publish activities or announcements.
- Manage staff accounts, roles, or permissions.
- Access financial operations or financial reports.
- Access records outside their assigned zone.

### 3.3 Pastor

The Pastor may:

- View member records across all zones.
- Create and edit member records across all zones.
- Transfer members between zones.
- Manage zones and Zone Leader assignments.
- Create zone-specific and church-wide attendance sessions.
- Record member attendance.
- Record visitor counts.
- View church-wide attendance reports.
- Publish activities and announcements.
- Create and edit donations.
- Create and edit daily fund records.
- Authorise or reject financial records.
- View financial dashboards and reports.
- Review financial audit history.

The Pastor does not receive staff-account management,
role-management, or system-configuration permissions
unless explicitly specified by an approved policy.

### 3.4 Administrator

The Administrator may:

- Manage staff accounts.
- Manage roles and permissions.
- Manage system configuration.
- Publish activities and announcements.
- Create and edit donations.
- Create and edit daily fund records.
- Authorise or reject financial records.
- View financial dashboards and reports.
- Review financial audit history.
- View general audit logs.

Administrator access to member data is not implied by
technical administration privileges.

Any future member-data permission requires an explicit
policy decision and separate permission design.

## 4. Zone-Based Access

Zone Leaders are restricted to their assigned zone.

The backend must enforce zone restrictions for:

- Member retrieval.
- Member creation and editing.
- Attendance session operations.
- Member attendance operations.
- Visitor-count operations.
- Attendance reports.
- Nested and related-object operations.

A request must not bypass zone restrictions by using
a direct object identifier, nested endpoint, export,
or another API operation.

Pastor access to member and attendance records is
church-wide within the defined Release 1 permissions.

## 5. Financial Access

Financial access is restricted to Pastor and Administrator.

Both roles may:

- Create and edit donations.
- Create and edit daily fund records.
- Authorise or reject pending financial records.
- View financial dashboards and reports.
- Review financial audit history.

Financial records follow the defined authorisation workflow.

Only authorised financial source records and authorised
adjustments are included in confirmed financial totals.

Authorised financial records must not be edited in place.
Corrections must use the approved linked correction
or reversal workflow.

## 6. Backend Enforcement

The backend must enforce permissions for every protected operation.

Permission checks must cover:

- List and retrieve operations.
- Create, update, and delete operations.
- Nested resources.
- Exports and reports.
- Financial operations.
- Staff and role administration.
- Audit-log access.

Unauthorised requests must be rejected.

Object-level permission checks must be applied even when
the user has permission to access the general endpoint.

## 7. Audit Requirements

Sensitive operations must identify the responsible actor
and produce attributable audit events according to
the audit policy.

Relevant operations include:

- Member changes.
- Staff and role administration.
- Attendance corrections.
- Publication operations.
- Financial operations.

The detailed audit-event schema and retention policy
must be defined in the audit policy.

## 8. Policy Limitations

This document does not independently establish:

- Financial self-approval rules.
- Separation-of-duties requirements.
- Additional Administrator member-data permissions.
- Permissions not specified in the Release 1 requirements.

These matters require an approved policy decision
before implementation.

## 9. Source

Source: Taunggyi City Church Community Management System
OOAD and System Design, Section 5, Roles and Permission Model.

This document represents the proposed Release 1
permission model and must remain consistent with
the approved requirements.
