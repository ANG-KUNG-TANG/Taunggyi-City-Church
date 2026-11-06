# Database Design

**Project:** Taunggyi City Church Community Management System
**Document:** Database Design
**Version:** 1.0
**Status:** Proposed Release 1
**Source:** OOAD & System Design, Sections 19.1–19.4
**Purpose:** Database structure, relationships, constraints, indexes, and implementation status

---

## 1. Purpose

This document defines the proposed database design for the Taunggyi City Church Community Management System.

It describes:

- Database entities and their responsibilities.
- Table fields and data types.
- Primary and foreign keys.
- Relationships between entities.
- Database constraints and indexes.
- Financial data integrity and authorization.
- Audit requirements.
- The relationship between the proposed database design and the current Django implementation.

The design follows the database specification in the project's OOAD document.

This document describes the **proposed Release 1 database design**. It does not establish that every specified table, field, constraint, or index has already been implemented.

## 2. Design Scope

The database supports the following system areas:

1. Staff accounts and role management.
2. Zone management and zone leader assignments.
3. Church member management.
4. Activities and announcements.
5. Attendance sessions and attendance records.
6. Visitor counting.
7. Donation management.
8. Fund transactions.
9. Financial adjustments and authorizations.
10. Audit logging.

The database distinguishes staff authentication accounts from church member profiles.

Members do not automatically require login accounts in Release 1.

## 3. Database Design Principles

### 3.1 Primary keys

The proposed database uses UUID primary keys for the domain entities specified in the OOAD.

Each entity must have a stable identifier that does not depend on its name, email address, or other mutable business attributes.

### 3.2 Relationships

Relationships must be represented through foreign keys wherever the relationship is between database entities.

Foreign keys should enforce referential integrity rather than relying exclusively on application-level validation.

### 3.3 Data integrity

Important business rules should be enforced at the database level whenever possible.

Examples include:

- Required member zone.
- Unique attendance record per session and member.
- Positive financial transaction amount.
- Non-negative visitor count.
- Valid financial authorization target.
- Anonymous donation identity restrictions.

### 3.4 Timestamps

Timestamp fields should use timezone-aware values where specified.

Server-generated timestamps should be used for system events such as record creation, updates, authorization, and audit logging.

### 3.5 Financial precision

Financial amounts use `NUMERIC(14,2)`.

The system must not use floating-point values for persisted financial amounts.

Currency must be explicitly represented using a currency code.

### 3.6 Separation of concerns

The database distinguishes:

- User account from member profile.
- User role from zone leader assignment.
- Attendance session from attendance record.
- Financial transaction from financial adjustment.
- Financial transaction from authorization decision.
- Domain record from audit log.

These distinctions must remain consistent throughout implementation.

## 4. Database Entity Inventory

The following tables are specified by the OOAD.

| Table | Responsibility |
|---|---|
| User | Staff authentication identity |
| Role | Staff role definition |
| UserRole | User-to-role assignment |
| Zone | Church operational zone |
| ZoneLeaderAssignment | Historical zone leader assignment |
| Member | Church member profile |
| Activity | Church activity information |
| Announcement | Church announcement information |
| AttendanceSession | Attendance session |
| MemberAttendance | Member attendance record |
| VisitorCount | Visitor count for a session |
| FinancialCategory | Donation or fund category |
| Donation | Donation transaction |
| FundTransaction | Fund income or expense |
| FinancialAdjustment | Financial correction or reversal |
| FinancialAuthorization | Financial decision history |
| AuditLog | Audit event record |

The table inventory represents the proposed database design, not the current migration inventory.

## 5. Identity and Access Management

### 5.1 User

**Purpose:** Represents a staff login identity.

Proposed table: `accounts_user`

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| email | VARCHAR(254) | Required, normalized, unique |
| password | Password hash | Required |
| first_name | VARCHAR | Nullable |
| last_name | VARCHAR | Nullable |
| is_active | BOOLEAN | Required, default true |
| last_login | TIMESTAMPTZ | Nullable |
| created_at | TIMESTAMPTZ | Required |

The User entity represents authentication and staff identity.

The physical table name must be reconciled with the existing Django model before implementation.

### 5.2 Role

**Purpose:** Defines a system role.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| code | VARCHAR(40) | Required, unique |
| name | VARCHAR | Required |
| description | TEXT | Nullable |
| is_system_role | BOOLEAN | Required |

Role definitions are separate from individual user accounts.

### 5.3 UserRole

**Purpose:** Represents the relationship between a user and a role.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | Required, FK to User |
| role_id | UUID | Required, FK to Role |
| assigned_by | UUID | Nullable, FK to User |
| assigned_at | TIMESTAMPTZ | Required |
| revoked_at | TIMESTAMPTZ | Nullable |

This table supports role assignment and assignment history.

The OOAD identifies a possible one-active-primary-role configuration for Release 1, but the multiple-role policy remains subject to confirmation.

### 5.4 Identity and member distinction

The database must maintain separate concepts:

**User account**

A staff identity with authentication credentials and role assignments.

**Member profile**

A church community record containing member information and one current zone.

A member is not automatically a User and does not automatically have a login account.

## 6. Zone and Member Management

### 6.1 Zone

**Purpose:** Represents an operational church zone.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| code | VARCHAR | Required, unique |
| name | VARCHAR | Required |
| description | TEXT | Nullable |
| is_active | BOOLEAN | Required |
| created_at | TIMESTAMPTZ | Required |
| updated_at | TIMESTAMPTZ | Required |

A zone may have multiple members.

Zone deactivation must not silently orphan member records.

### 6.2 ZoneLeaderAssignment

**Purpose:** Connects a staff User to a Zone for a defined period.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | Required, FK to User |
| zone_id | UUID | Required, FK to Zone |
| assigned_by | UUID | Required, FK to User |
| starts_at | TIMESTAMPTZ | Required |
| ends_at | TIMESTAMPTZ | Nullable |
| created_at | TIMESTAMPTZ | Required |

The assignment represents operational responsibility.

It does not represent the member's zone.

Assignment history must be retained.

The database must validate:

`ends_at IS NULL OR ends_at > starts_at`

### 6.3 Member

**Purpose:** Represents a church member profile.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| zone_id | UUID | Required, FK to Zone |
| full_name | VARCHAR | Required |
| phone | VARCHAR | Nullable |
| address | TEXT | Nullable |
| notes | TEXT | Nullable |
| is_active | BOOLEAN | Required |
| created_by | UUID | Required, FK to User |
| updated_by | UUID | Required, FK to User |
| created_at | TIMESTAMPTZ | Required |
| updated_at | TIMESTAMPTZ | Required |

Every member must belong to exactly one current zone.

The zone relationship is mandatory.

Member transfer must update the current zone without confusing the member's identity with the zone leader assignment.

## 7. Activities and Announcements

### 7.1 Activity

**Purpose:** Stores church activity information.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| title | VARCHAR | Required |
| body | TEXT | Required |
| status | VARCHAR(20) | Required |
| published_by | UUID | Nullable, FK to User |
| published_at | TIMESTAMPTZ | Nullable |
| created_at | TIMESTAMPTZ | Required |
| updated_at | TIMESTAMPTZ | Required |

Allowed status values:

- `DRAFT`
- `PUBLISHED`
- `ARCHIVED`

Published activities may be associated with attendance sessions.

### 7.2 Announcement

**Purpose:** Stores church announcement information.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| title | VARCHAR | Required |
| body | TEXT | Required |
| status | VARCHAR(20) | Required |
| published_by | UUID | Nullable, FK to User |
| published_at | TIMESTAMPTZ | Nullable |
| created_at | TIMESTAMPTZ | Required |
| updated_at | TIMESTAMPTZ | Required |

Allowed status values:

- `DRAFT`
- `PUBLISHED`
- `ARCHIVED`

Publication must be performed by an authorized staff member.

## 8. Attendance Management

### 8.1 AttendanceSession

**Purpose:** Represents a church or zone attendance session.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| activity_id | UUID | Nullable, FK to Activity |
| starts_at | TIMESTAMPTZ | Required |
| scope | VARCHAR(20) | Required |
| zone_id | UUID | Nullable, FK to Zone |
| status | VARCHAR(20) | Required |
| created_by | UUID | Required, FK to User |
| created_at | TIMESTAMPTZ | Required |
| updated_at | TIMESTAMPTZ | Required |

Allowed scope values:

- `ZONE`
- `CHURCH_WIDE`

Allowed status values:

- `DRAFT`
- `OPEN`
- `CLOSED`
- `ARCHIVED`

Scope constraint:

- For `ZONE`, `zone_id` must be populated.
- For `CHURCH_WIDE`, `zone_id` must be null.

The scope and zone relationship must be validated together.

### 8.2 MemberAttendance

**Purpose:** Records a member's attendance in a session.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| session_id | UUID | Required, FK to AttendanceSession |
| member_id | UUID | Required, FK to Member |
| status | VARCHAR(20) | Required |
| recorded_by | UUID | Required, FK to User |
| recorded_at | TIMESTAMPTZ | Required |
| updated_by | UUID | Nullable, FK to User |
| updated_at | TIMESTAMPTZ | Nullable |

Allowed status values:

- `PRESENT`
- `ABSENT`

A member must have at most one attendance record per session.

The database must enforce:

`UNIQUE(session_id, member_id)`

### 8.3 VisitorCount

**Purpose:** Stores aggregate visitor counts by category for an
attendance session.

Release 1 supports the following categories:

- `FIRST_TIME`: First-time visitors.
- `RETURNING`: Returning visitors.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| session_id | UUID | Required, FK to AttendanceSession |
| category | VARCHAR(20) | Required, permitted category |
| count | INTEGER | Required, non-negative |
| recorded_by | UUID | Required, FK to User |
| recorded_at | TIMESTAMPTZ | Required |
| updated_by | UUID | Nullable, FK to User |
| updated_at | TIMESTAMPTZ | Nullable |

Constraints:

- `count >= 0`
- `category IN ('FIRST_TIME', 'RETURNING')`
- `UNIQUE(session_id, category)`

Each VisitorCount record belongs to exactly one AttendanceSession.

An AttendanceSession may have multiple VisitorCount records,
but no more than one record for each supported category.

The total visitor count for a session is calculated as the sum
of its FIRST_TIME and RETURNING counts.

A missing category record means that the count has not been
recorded. A count of zero means that the category was recorded
and no visitors were counted.

Individual visitor identity records are outside Release 1 scope.

## 9. Financial Management

Financial data requires strict integrity, authorization, and audit controls.

Financial records must distinguish pending transactions from authorized transactions.

### 9.1 FinancialCategory

**Purpose:** Defines donation and fund categories.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| code | VARCHAR | Required, unique |
| name | VARCHAR | Required |
| scope | VARCHAR(20) | Required |
| is_active | BOOLEAN | Required |
| description | TEXT | Nullable |
| created_by | UUID | Required, FK to User |
| created_at | TIMESTAMPTZ | Required |
| updated_at | TIMESTAMPTZ | Required |

Allowed scope values:

- `DONATION`
- `FUND`
- `BOTH`

The category scope must match the financial transaction type.

### 9.2 Donation

**Purpose:** Records a donation transaction.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| transaction_date | DATE | Required |
| amount | NUMERIC(14,2) | Required, greater than zero |
| currency_code | CHAR(3) | Required |
| category_id | UUID | Required, FK to FinancialCategory |
| payment_method | VARCHAR | Required |
| donor_identity | Nullable identity field | Nullable |
| is_anonymous | BOOLEAN | Required |
| notes | TEXT | Nullable |
| status | VARCHAR(20) | Required |
| created_by | UUID | Required, FK to User |
| created_at | TIMESTAMPTZ | Required |
| updated_by | UUID | Required, FK to User |
| updated_at | TIMESTAMPTZ | Required |
| authorised_by | UUID | Nullable, FK to User |
| authorised_at | TIMESTAMPTZ | Nullable |

Allowed status values:

- `PENDING`
- `AUTHORISED`
- `REJECTED`

Constraints:

- Amount must be greater than zero.
- Currency code is required.
- Category must support donations.
- Anonymous donations must not store donor identity.

Anonymity constraint:

`is_anonymous = FALSE OR donor_identity IS NULL`

### 9.3 FundTransaction

**Purpose:** Records fund income or expenditure.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| transaction_date | DATE | Required |
| amount | NUMERIC(14,2) | Required, greater than zero |
| currency_code | CHAR(3) | Required |
| category_id | UUID | Required, FK to FinancialCategory |
| transaction_type | VARCHAR(20) | Required |
| notes | TEXT | Nullable |
| status | VARCHAR(20) | Required |
| created_by | UUID | Required, FK to User |
| created_at | TIMESTAMPTZ | Required |
| updated_by | UUID | Required, FK to User |
| updated_at | TIMESTAMPTZ | Required |
| authorised_by | UUID | Nullable, FK to User |
| authorised_at | TIMESTAMPTZ | Nullable |

Proposed transaction types:

- `INCOME`
- `EXPENSE`

Allowed status values:

- `PENDING`
- `AUTHORISED`
- `REJECTED`

Constraints:

- Amount must be greater than zero.
- Currency code is required.
- Category must support fund transactions.

### 9.4 FinancialAdjustment

**Purpose:** Represents a correction or reversal associated with an original financial record.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| donation_id | UUID | Nullable, FK to Donation |
| fund_transaction_id | UUID | Nullable, FK to FundTransaction |
| adjustment_type | VARCHAR(20) | Required |
| amount_delta | NUMERIC(14,2) | Required, non-zero |
| reason | TEXT | Required |
| status | VARCHAR(20) | Required |
| created_by | UUID | Required, FK to User |
| updated_by | UUID | Nullable, FK to User |
| created_at | TIMESTAMPTZ | Required |
| updated_at | TIMESTAMPTZ | Required |

Allowed adjustment types:

- `CORRECTION`
- `REVERSAL`

Allowed status values:

- `PENDING`
- `AUTHORISED`
- `REJECTED`

Exactly one source must be populated:

- `donation_id`
- `fund_transaction_id`

The database must enforce the exclusive relationship.

The adjustment must have a non-zero amount delta and a mandatory reason.

### 9.5 FinancialAuthorization

**Purpose:** Stores financial authorization decisions.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| donation_id | UUID | Nullable, FK to Donation |
| fund_transaction_id | UUID | Nullable, FK to FundTransaction |
| adjustment_id | UUID | Nullable, FK to FinancialAdjustment |
| decision | VARCHAR(20) | Required |
| decided_by | UUID | Required, FK to User |
| decided_at | TIMESTAMPTZ | Required |
| reason | TEXT | Nullable |

Allowed decision values:

- `AUTHORISE`
- `REJECT`

Exactly one target reference must be populated:

- `donation_id`
- `fund_transaction_id`
- `adjustment_id`

A rejection requires a reason.

Authorization decisions must be retained as historical records rather than silently overwritten.

## 10. Audit Logging

### 10.1 AuditLog

**Purpose:** Records important system and business events.

| Field | Type | Constraint |
|---|---|---|
| id | UUID | Primary key |
| actor_id | UUID | Nullable, FK to User |
| entity_type | VARCHAR(80) | Required |
| entity_id | UUID | Required |
| action | VARCHAR(40) | Required |
| before_data | JSONB | Nullable |
| after_data | JSONB | Nullable |
| occurred_at | TIMESTAMPTZ | Required |
| correlation_id | UUID | Nullable |

The actor may be null only for system or security events.

The entity identifier is a polymorphic reference represented by `entity_type` and `entity_id`.

Audit actions may include:

- `CREATE`
- `UPDATE`
- `AUTHORISE`
- `REJECT`
- `CORRECT`
- `REVERSE`
- `PUBLISH`
- `ROLE_CHANGE`

Audit snapshots must be redacted.

Secrets and unnecessary personal data must not be stored in audit snapshots.

Ordinary UPDATE and DELETE operations on audit records are prohibited by the OOAD specification.

## 11. Relationships

| Relationship | Cardinality | Rule |
|---|---|---|
| User — Role | Many-to-many | Through UserRole |
| User — UserRole | One-to-many | Role assignment history |
| Role — UserRole | One-to-many | Role assignment history |
| User — ZoneLeaderAssignment | One-to-many | Assignment history |
| Zone — ZoneLeaderAssignment | One-to-many | Zone assignment history |
| Zone — Member | One-to-many | Member zone is required |
| Activity — AttendanceSession | One-to-many | Session may have no Activity |
| Zone — AttendanceSession | One-to-many | Conditional on session scope |
| AttendanceSession — MemberAttendance | One-to-many | Attendance records |
| Member — MemberAttendance | One-to-many | Member attendance history |
| AttendanceSession — VisitorCount | One-to-many | Visitor count records |
| FinancialCategory — Donation | One-to-many | Donation category |
| FinancialCategory — FundTransaction | One-to-many | Fund category |
| Donation — FinancialAdjustment | One-to-many | Donation corrections/reversals |
| FundTransaction — FinancialAdjustment | One-to-many | Fund corrections/reversals |
| Donation — FinancialAuthorization | One-to-many | Decision history |
| FundTransaction — FinancialAuthorization | One-to-many | Decision history |
| FinancialAdjustment — FinancialAuthorization | One-to-many | Decision history |
| User — AuditLog | One-to-many | Actor history |

## 12. Critical Constraints

### 12.1 Member

- `zone_id` is required.
- `zone_id` references Zone.
- Member records must not have a null zone.

### 12.2 ZoneLeaderAssignment

- User, Zone, and assigning User references must be valid.
- `ends_at` must be null or later than `starts_at`.
- Assignment history must be retained.

### 12.3 AttendanceSession

- Scope must be a permitted value.
- Status must be a permitted value.
- Zone scope requires `zone_id`.
- Church-wide scope requires `zone_id` to be null.

### 12.4 MemberAttendance

- Session and Member references must be valid.
- Status must be `PRESENT` or `ABSENT`.
- A member can have only one record per session.

### 12.5 VisitorCount

- Count must be greater than or equal to zero.
- Count must be an integer.
- Session reference is required.
- Category is required.
- Category must be `FIRST_TIME` or `RETURNING`.
- Each category may appear only once per session.
- The combination of `session_id` and `category` must be unique.
- Visitor counts must remain aggregate-only.
- Individual visitor identity records are outside Release 1 scope.

### 12.6 Donation and FundTransaction

- Amount must be greater than zero.
- Currency code is required.
- Financial category must match the transaction scope.
- Status must be valid.
- Pending records must not be treated as confirmed totals.

### 12.7 Donation anonymity

- Anonymous donations must not retain donor identity.
- Named-donor search indexes are permitted only if the privacy policy allows them.

### 12.8 FinancialAdjustment

- Exactly one source reference must be populated.
- Amount delta must not equal zero.
- Reason is required.

### 12.9 FinancialAuthorization

- Exactly one target reference must be populated.
- Decision must be `AUTHORISE` or `REJECT`.
- Decision actor and timestamp are required.
- Rejection reason is required.

### 12.10 AuditLog

- Ordinary UPDATE and DELETE operations are prohibited.
- Entity type and action are required.
- Actor may be null only for system/security events.

## 13. Index Design

The following indexes are specified or suggested by the OOAD.

| Table | Index | Purpose |
|---|---|---|
| Member | `(zone_id, is_active)` | Zone member filtering |
| Member | Approved name search index | Member search |
| ZoneLeaderAssignment | `(user_id, ends_at)` | Current assignment lookup |
| ZoneLeaderAssignment | `(zone_id, ends_at)` | Zone assignment lookup |
| AttendanceSession | `(zone_id, starts_at)` | Zone attendance history |
| AttendanceSession | `(scope, starts_at)` | Scope-based attendance history |
| MemberAttendance | `(session_id, member_id)` unique | Prevent duplicate attendance |
| MemberAttendance | `(member_id)` | Member attendance history |
| VisitorCount | `(session_id)` | Session visitor count lookup |
| Donation | `(transaction_date, status)` | Donation reporting |
| Donation | Category index | Category reporting |
| FundTransaction | `(transaction_date, status)` | Fund reporting |
| FundTransaction | Category index | Category reporting |
| FinancialAdjustment | `(donation_id, status)` | Donation adjustment lookup |
| FinancialAdjustment | `(fund_transaction_id, status)` | Fund adjustment lookup |
| FinancialAuthorization | Target foreign key indexes | Decision lookup |
| FinancialAuthorization | `(decided_at)` | Decision history |
| AuditLog | `(entity_type, entity_id, occurred_at)` | Entity audit history |
| AuditLog | `(actor_id, occurred_at)` | Actor audit history |

A partial index for named-donor searches must be considered only after the privacy policy has been approved.

Indexes must be reviewed against actual query patterns before migration.

## 14. Existing Django Implementation

### 14.1 Current User model

The current Django project contains a custom User model.

Its existing implementation includes fields and behavior such as:

- Name.
- Email.
- Phone.
- Gender.
- Marital status.
- Date of birth.
- Testimony.
- Baptism date.
- Membership date.
- Role.
- Status.
- Staff and superuser flags.
- Active status.
- Notification settings.

The current model uses the Django authentication framework.

Its configured authentication model is:

`AUTH_USER_MODEL = "tcc.User"`

The model currently uses the physical table name:

`users`

### 14.2 Existing migration

The current initial migration creates the User model.

The current migration baseline does not establish the complete database described in Section 19 of the OOAD.

The remaining domain model files are scaffolds and must not be treated as implemented database tables.

### 14.3 User model reconciliation

The OOAD proposes a staff User structure containing authentication and role-related information.

The existing Django User model already contains additional church-related profile fields and role/status choices.

Before implementation:

1. Preserve the existing custom authentication model.
2. Compare existing fields with the OOAD User requirements.
3. Identify missing fields.
4. Determine whether role assignments should use the proposed UserRole table.
5. Avoid creating a second User table.
6. Confirm the physical table name and app label.
7. Create migrations only after the model changes have been reviewed.

The OOAD table name `accounts_user` must not be assumed to be the physical table name in the current Django implementation.

### 14.4 Implementation status

| Area | OOAD specification | Current implementation status |
|---|---|---|
| User | Defined | Existing custom model and initial migration |
| Role | Defined | Scaffold; not established by current migration |
| UserRole | Defined | Scaffold; not established by current migration |
| Zone | Defined | Scaffold; not established by current migration |
| ZoneLeaderAssignment | Defined | Scaffold; not established by current migration |
| Member | Defined | Scaffold; not established by current migration |
| Activity | Defined | Scaffold; not established by current migration |
| Announcement | Defined | Scaffold; not established by current migration |
| AttendanceSession | Defined | Scaffold; not established by current migration |
| MemberAttendance | Defined | Scaffold; not established by current migration |
| VisitorCount | Defined | Scaffold; not established by current migration |
| FinancialCategory | Defined | Scaffold; not established by current migration |
| Donation | Defined | Scaffold; not established by current migration |
| FundTransaction | Defined | Scaffold; not established by current migration |
| FinancialAdjustment | Defined | Scaffold; not established by current migration |
| FinancialAuthorization | Defined | Scaffold; not established by current migration |
| AuditLog | Defined | Scaffold; not established by current migration |

## 15. Migration Strategy

Database implementation should proceed incrementally.

### Step 1: Reconcile User

Review the existing custom User model against the OOAD.

Do not replace the existing authentication model without an explicit design decision.

### Step 2: Implement identity and role tables

Implement:

- Role.
- UserRole.

Confirm the role assignment policy before finalizing constraints.

### Step 3: Implement zones and members

Implement:

- Zone.
- ZoneLeaderAssignment.
- Member.

Enforce the required member zone relationship.

### Step 4: Implement activities and attendance

Implement:

- Activity.
- Announcement.
- AttendanceSession.
- MemberAttendance.
- VisitorCount.

Validate session scope and attendance uniqueness.

### Step 5: Implement financial tables

Implement:

- FinancialCategory.
- Donation.
- FundTransaction.
- FinancialAdjustment.
- FinancialAuthorization.

Financial constraints and authorization history must be reviewed before the finance workflow is enabled.

### Step 6: Implement audit logging

Implement AuditLog and ensure important business operations create appropriate audit events.

### Step 7: Validate migrations

After each implementation stage:

- Review generated migrations.
- Confirm foreign keys.
- Confirm unique constraints.
- Confirm check constraints.
- Confirm indexes.
- Run Django system checks.
- Test migration application.
- Test rollback behavior where appropriate.

## 16. Open Design Decisions

The following decisions must remain explicit until approved.

| Decision | Current position |
|---|---|
| Multiple active roles per User | OOAD identifies this as requiring confirmation |
| One active primary role per User | Proposed Release 1 configuration |
| Physical User table name | Existing Django table is `users`; reconcile with OOAD |
| Zone leader assignment uniqueness | Confirm whether overlapping assignments are permitted |
| Member transfer history | OOAD specifies current zone and assignment history; additional member-zone history is not established here |
| Financial payment method values | Subject to policy approval |
| Supported currency values | Explicit currency code required; permitted currencies need confirmation |
| Named-donor search | Requires privacy policy approval |
| Financial correction and reversal workflow | Must follow authorization requirements |
| Audit snapshot contents | Must be redacted and privacy-reviewed |

These decisions must not be silently resolved during model implementation.

## 17. Database Design Acceptance Criteria

The database design is ready for implementation review when:

- [ ] Every OOAD entity has a documented table.
- [ ] Each table has a defined primary key.
- [ ] Required foreign keys are identified.
- [ ] Relationship cardinalities are documented.
- [ ] Required fields and nullability are specified.
- [ ] Financial amounts use decimal precision.
- [ ] Financial currency is explicit.
- [ ] Member zone is mandatory.
- [ ] Attendance uniqueness is enforced.
- [ ] Session scope and zone consistency are enforced.
- [ ] Financial authorization target exclusivity is enforced.
- [ ] Financial adjustment source exclusivity is enforced.
- [ ] Anonymous donation identity constraints are enforced.
- [ ] Audit requirements are documented.
- [ ] Existing Django User differences are identified.
- [ ] Proposed tables are clearly distinguished from implemented tables.
- [ ] Open decisions remain visible.

## 18. Source

Primary source:

**Taunggyi City Church Community Management System — OOAD & System Design**

Relevant sections:

- Section 19.1 — Database table specifications.
- Section 19.2 — Critical database constraints and indexes.
- Section 19.3 — Relationship summary.
- Section 19.4 — Account/profile/assignment distinction.

This document follows the proposed Release 1 database specification and identifies the existing Django implementation separately.

---

**End of Database Design**
