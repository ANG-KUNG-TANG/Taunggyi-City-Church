# Taunggyi City Church Community Management System
## Domain Model

**Document:** Domain Model
**Version:** 1.0
**Status:** Proposed Release 1 design
**Last updated:** 6 November 2026

---

## 1. Purpose

This document defines the proposed domain model for the Taunggyi City Church Community Management System.

It identifies the principal business entities, their responsibilities, relationships, and integrity constraints.

The model follows the consolidated Release 1 OOAD and System Design Specification. It distinguishes church member profiles from staff authentication accounts and preserves the approved role, zone, attendance, and financial restrictions.

This document describes the intended design. It does not claim that every entity or relationship has already been implemented.

## 2. Domain Scope

The Release 1 domain includes:

- Staff accounts and role assignments.
- Member profiles and zone management.
- Attendance sessions and member attendance records.
- Aggregate visitor counts.
- Activities and announcements.
- Donation and fund transactions.
- Financial authorisation and correction history.
- Audit records.

Member self-service accounts and individual visitor profiles are outside Release 1 scope.

## 3. Domain Model Principles

1. A member is a church business profile, not an authentication account.
2. Every member has exactly one current zone.
3. Zone Leaders operate only within their assigned zone.
4. Zone Leaders cannot transfer members between zones.
5. Attendance sessions support zone-specific and church-wide scope.
6. Attendance status is limited to Present or Absent in Release 1.
7. Visitor information is stored as aggregate counts.
8. Financial access is restricted to Pastor and Administrator.
9. New financial records enter Pending status.
10. Authorised financial records are immutable in place.
11. Financial corrections use linked adjustment or reversal records.
12. Sensitive operations must be attributable to an authenticated actor.

## 4. Core Entities

### 4.1 StaffAccount

Represents a staff member who can authenticate and access protected system functions.

Responsibilities:

- Authenticate staff users.
- Maintain account status.
- Associate an account with its authorised role.
- Record account creation and relevant updates.
- Support controlled staff administration.

A StaffAccount is separate from a Member profile.

### 4.2 Role

Represents a system role used to determine permitted operations.

Release 1 roles:

- Pastor
- Administrator
- Zone Leader

Responsibilities:

- Define the access category of a staff account.
- Support backend role-based authorisation.
- Restrict access to protected functions.

Role permissions must be enforced by the backend. Frontend visibility is not an authorisation boundary.

### 4.3 Zone

Represents a church zone used to organise members and zone-specific attendance operations.

Responsibilities:

- Identify a zone.
- Maintain zone information.
- Provide the scope for member and attendance access.
- Support Pastor-managed Zone Leader assignments.

Zone management is a Pastor responsibility.

### 4.4 Member

Represents a church member's business profile.

Responsibilities:

- Store member information required by the approved member workflow.
- Maintain one current zone association.
- Support member viewing, creation, and editing.
- Provide member references for attendance records.

Constraints:

- A member must have a current zone.
- A member belongs to exactly one current zone.
- A Zone Leader may create or edit members only within the assigned zone.
- A Zone Leader cannot transfer a member to another zone.
- Member login is not part of Release 1.

The detailed member attributes must follow the approved requirements and database specification.

### 4.5 ZoneLeaderAssignment

Represents the association between a Zone Leader staff account and a zone.

Responsibilities:

- Record which zone a Zone Leader is assigned to.
- Support zone-scoped authorisation.
- Record assignment actor and effective information.
- Allow Pastor-managed assignment changes.

The backend must check the active assignment when a Zone Leader accesses zone-specific records.

The assignment history must retain sufficient information to identify who made the assignment and when it became effective.

### 4.6 Activity

Represents a church activity that may be published and may be associated with attendance.

Responsibilities:

- Store activity information.
- Support authorised activity publication.
- Provide an optional association for an attendance session.

Only authorised publishing roles may publish activities.

The exact activity fields and publication states must follow the approved requirements.

### 4.7 Announcement

Represents church information intended for publication.

Responsibilities:

- Store announcement content.
- Support authorised publication.
- Provide published information to public-facing interfaces.

Only published announcements may be returned through public content endpoints.

### 4.8 AttendanceSession

Represents an attendance event for a specific date and scope.

Responsibilities:

- Define the session date and scope.
- Associate a session with a zone when zone-specific.
- Support session lifecycle management.
- Provide the context for member attendance and visitor counts.

Supported scope:

- ZONE
- CHURCH_WIDE

Supported lifecycle states:

- DRAFT
- OPEN
- CLOSED
- ARCHIVED

Constraints:

- A zone-specific session requires a zone.
- A church-wide session has no zone association.
- Zone Leaders may create zone-specific sessions within their assigned zone.
- Zone Leaders cannot create church-wide sessions.
- Closed sessions cannot be silently modified.

An optional Activity association may connect the session to a church activity.

### 4.9 MemberAttendance

Represents the attendance status of one member in one attendance session.

Responsibilities:

- Associate a member with an attendance session.
- Record the member's attendance status.
- Support attendance reporting.
- Preserve the session/member relationship.

Supported status values:

- PRESENT
- ABSENT

Constraints:

- Attendance may be recorded only for an eligible member and an open session.
- The session and member must satisfy the applicable zone scope.
- Duplicate attendance for the same session/member pair is prohibited.
- Closed-session corrections must follow the controlled correction policy.

### 4.10 VisitorCount

Represents the aggregate number of visitors recorded for a specific
category within an attendance session.

Release 1 supports the following visitor categories:

- FIRST_TIME: First-time visitors.
- RETURNING: Returning visitors.

Responsibilities:

- Record visitor counts by category for an attendance session.
- Support aggregate visitor reporting.
- Calculate the total visitor count for a session.
- Preserve aggregate visitor information without creating individual
  visitor profiles.

Constraints:

- Visitor counts must be non-negative integers.
- Each attendance session may have at most one record per visitor category.
- Each visitor-count record belongs to exactly one attendance session.
- The total visitor count is the sum of the FIRST_TIME and RETURNING
  category counts.
- Individual visitor identity records are outside Release 1 scope.

A session may contain multiple VisitorCount records, one for each
supported category.

The absence of a VisitorCount record means that the category has
not yet been recorded. A recorded count of zero means that the
category was recorded and no visitors were counted.

### 4.11 Donation

Represents a donation transaction.

Responsibilities:

- Record donation information.
- Support controlled creation and editing.
- Maintain financial status.
- Provide a source record for financial reporting.
- Support linked corrections or reversals.

Financial access is restricted to Pastor and Administrator.

A donation record includes the approved transaction information, such as date, amount, currency, category, payment method, optional donor identity, and notes.

Constraints:

- New donations enter Pending status.
- Amount and category must be validated.
- Donor identity must respect the approved anonymity requirements.
- Authorised records cannot be edited in place.
- Corrections must use linked adjustment or reversal records.

### 4.12 FundTransaction

Represents a daily fund movement.

Responsibilities:

- Record fund income or expense.
- Maintain transaction information.
- Support financial authorisation.
- Provide source data for financial reporting.
- Support linked corrections or reversals.

Financial access is restricted to Pastor and Administrator.

Constraints:

- New fund transactions enter Pending status.
- Transaction type and category must be validated.
- Authorised source records cannot be edited in place.
- Corrections must use linked adjustment or reversal records.

### 4.13 FinancialAuthorization

Represents a decision to authorise or reject a financial record.

Responsibilities:

- Associate a decision with a financial record.
- Record the decision actor and timestamp.
- Preserve the decision history.
- Support controlled status transitions.

Financial decisions must be attributable and immutable.

The policy governing self-approval and separation of duties remains unresolved and must be confirmed before implementation.

### 4.14 FinancialAdjustment

Represents a correction or reversal linked to an authorised financial source record.

Responsibilities:

- Identify the original financial record.
- Record the correction or reversal.
- Preserve the original record.
- Support a separate authorisation decision.
- Provide an auditable financial history.

Constraints:

- The original authorised record remains unchanged.
- The adjustment must reference its original record.
- The adjustment enters Pending status.
- Only authorised adjustments affect confirmed financial totals.
- Correction reasons and audit history are required.

### 4.15 AuditEvent

Represents an attributable record of a sensitive system operation.

Responsibilities:

- Identify the actor.
- Record the operation and affected resource.
- Preserve event timing.
- Support audit review.

Audit events are required for sensitive actions, including relevant member changes, staff and role administration, attendance corrections, publication operations, and financial actions.

Audit records must not be treated as ordinary editable business records.

The exact event payload, retention period, and storage strategy must follow the audit policy.

## 5. Entity Relationships

The following relationships define the proposed domain structure.

| Relationship | Cardinality | Rule |
|---|---|---|
| Zone — Member | One-to-many | Each member has exactly one current zone. |
| StaffAccount — ZoneLeaderAssignment | One-to-many over assignment history | Assignments identify the staff account and zone. |
| Zone — ZoneLeaderAssignment | One-to-many over assignment history | Pastor manages Zone Leader assignments. |
| AttendanceSession — VisitorCount | One-to-many | Each session may have one record per supported visitor category. |
| Activity — AttendanceSession | One-to-many, optional from session | A session may reference an activity. |
| AttendanceSession — MemberAttendance | One-to-many | A session may contain multiple member attendance records. |
| Member — MemberAttendance | One-to-many | A member may attend multiple sessions. |
| Donation — FinancialAuthorization | One-to-many decision history | Decisions must remain attributable. |
| FundTransaction — FinancialAuthorization | One-to-many decision history | Decisions must remain attributable. |
| StaffAccount — AuditEvent | One-to-many | Audit events identify the responsible actor. |

The financial source relationship must be finalised in the database specification.

## 6. Financial Domain Rules

### 6.1 Status lifecycle

Financial records follow a controlled workflow:

- Pending
- Authorised
- Rejected

Only authorised source records and authorised adjustments are included in confirmed financial totals.

### 6.2 Authorisation

An authorisation decision must:

- Confirm that the record is Pending.
- Check the actor's finance permission.
- Record the decision.
- Preserve the decision history.
- Update the record status atomically.

A record that has already been decided cannot be silently decided again.

### 6.3 Corrections

Authorised records are immutable in place.

A correction must:

1. Reference the original authorised record.
2. Include a correction reason.
3. Create a linked adjustment or reversal.
4. Enter the controlled authorisation workflow.
5. Preserve the original record and its history.

Only authorised adjustments affect confirmed totals.

## 7. Access and Domain Boundaries

### Public

Public users may access published church information.

Public access does not include protected member, attendance, staff, or financial records.

### Zone Leader

Zone Leaders may access member and attendance operations within their assigned zone.

They cannot:

- Transfer members between zones.
- Create church-wide attendance sessions.
- Access finance functions.
- Access records outside their assigned zone.

### Pastor

Pastor has church-wide member, zone, attendance, and financial capabilities as defined by the approved permission model.

Pastor manages zones and Zone Leader assignments.

### Administrator

Administrator responsibilities include staff accounts, role administration, system configuration, publication, audit review, and explicitly approved financial permissions.

Administrator access to member data is not implied.

## 8. Integrity Constraints

The domain model must preserve the following constraints:

1. Every member has one current zone.
2. Members do not authenticate in Release 1.
3. Zone Leaders cannot transfer members.
4. Zone Leaders are restricted to their assigned zone.
5. Attendance status is Present or Absent.
6. Duplicate member/session attendance is prohibited.
7. Visitor counts are non-negative.
8. Visitor records do not contain individual visitor profiles.
9. Financial access is limited to Pastor and Administrator.
10. Financial records require controlled authorisation.
11. Authorised financial records are immutable in place.
12. Corrections are linked and auditable.
13. Confirmed financial totals include only authorised source records and authorised adjustments.
14. Sensitive operations identify the responsible actor.
15. Each attendance session may have one VisitorCount record per supported category: FIRST_TIME or RETURNING.

## 9. Unresolved Domain Decisions

The following matters must not be silently decided by implementation:

- Whether attendance is recorded by session, service, or another approved operational process.
- The final member attributes and required fields.
- The final Zone Leader assignment history model.
- The timezone and church-local date policy.
- Financial separation of duties and self-approval rules.
- Donation categories, fund types, currencies, and payment methods.
- Financial adjustment limits and reversal rules.
- Audit-event schema and retention period.

These decisions must be recorded in the open-decision register and approved by the appropriate church decision owner.

## 10. Traceability

This domain model supports the Release 1 requirements concerning:

- Staff authentication and role administration.
- Member creation, editing, viewing, and zone management.
- Zone Leader assignment.
- Attendance session management.
- Member attendance and visitor counts.
- Attendance reporting and correction.
- Activity and announcement publication.
- Donation and fund transaction workflows.
- Financial authorisation, reporting, correction, and audit.

The detailed requirement identifiers and acceptance criteria must remain traceable to the master OOAD specification.

## 11. Implementation Status

This document defines a proposed Release 1 domain model.

It is not evidence that all entities, relationships, constraints, or workflows have been implemented.

Implementation must be verified against the backend models, migrations, serializers, services, permissions, and tests.
