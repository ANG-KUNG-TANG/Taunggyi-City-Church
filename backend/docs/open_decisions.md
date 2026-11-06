# Open Decision Register

## 1. Purpose

This register records unresolved business, operational, and technical
decisions for the Taunggyi City Church Community Management System.

Decisions must not be silently introduced during implementation.

Each decision must be reviewed by the appropriate church decision
owner or project owner before it is treated as approved.

## 2. Decision Status

- OPEN: Decision has not been approved.
- PROPOSED: A candidate solution exists but requires approval.
- APPROVED: Decision has been confirmed by the responsible owner.
- DEFERRED: Decision is intentionally postponed and its impact is known.

No decision in this register is approved merely because it has
a proposed option.

## 3. Open Business and Operational Decisions

### OD-01 — Authentication and Session Strategy

Status: OPEN

Decision:
Confirm the final authentication approach and session/token
configuration for Release 1.

Questions:
- Which authentication mechanism will be used?
- What session or token lifecycle is required?
- What expiration and renewal rules apply?
- What logout and revocation behavior is required?

Source:
- architecture.md, Section 16
- architecture.md, Section 18

### OD-02 — Church Display Timezone

Status: OPEN

Decision:
Confirm the church display timezone and church-local date policy.

Questions:
- Which timezone governs attendance dates?
- Which timezone governs financial report date boundaries?
- How are timestamps displayed to users?
- How are date ranges interpreted?

Source:
- architecture.md, Section 16
- domain_model.md, Section 9
- finance_workflow.md, Sections 7 and 8

### OD-03 — Attendance Operating Workflow

Status: OPEN

Decision:
Confirm how attendance is organised and recorded.

Questions:
- Is attendance recorded by session, service, or another process?
- Who creates and manages attendance sessions?
- What session lifecycle is required?
- When may attendance be corrected?
- What operational rules govern church-wide and zone sessions?

Source:
- architecture.md, Section 16
- domain_model.md, Section 9

### OD-04 — Member Attributes

Status: OPEN

Decision:
Confirm the final member attributes and required fields.

Questions:
- Which member fields are required?
- Which fields are optional?
- Which fields are sensitive?
- Which fields may each role view or modify?

Source:
- domain_model.md, Section 9

### OD-05 — Zone Leader Assignment History

Status: OPEN

Decision:
Confirm the final Zone Leader assignment-history model.

Questions:
- Are overlapping assignments permitted?
- What rules govern assignment start and end dates?
- How is assignment history preserved?
- What constraints apply to current assignments?

Source:
- domain_model.md, Section 9
- database_design.md, Section 16

### OD-06 — Financial Categories and Fund Types

Status: OPEN

Decision:
Confirm approved donation categories and fund types.

Questions:
- Which categories are required?
- Are categories fixed or administrator-configurable?
- Which transaction scopes are permitted?
- What rules govern category activation and deactivation?

Source:
- architecture.md, Section 16
- finance_workflow.md, Section 11
- database_design.md, Section 16

### OD-07 — Supported Currencies

Status: OPEN

Decision:
Confirm the permitted currency values for Release 1.

The system must store an explicit currency code.
Currency conversion must not be assumed.

Questions:
- Which currencies may be recorded?
- Are multiple currencies permitted?
- Is exchange-rate conversion required?
- If conversion is required, which rate and date policy applies?

Source:
- database_design.md, Section 16
- finance_workflow.md, Sections 2 and 8

### OD-08 — Payment Methods

Status: OPEN

Decision:
Confirm the supported financial payment methods.

Questions:
- Which payment methods are supported?
- Are payment methods fixed or configurable?
- Are additional payment details required?

Source:
- database_design.md, Section 16
- finance_workflow.md, Section 11

### OD-09 — Financial Self-Approval and Separation of Duties

Status: OPEN

Decision:
Confirm whether a financial record creator may authorise
their own record and define separation-of-duties requirements.

Questions:
- May creators authorise their own transactions?
- Must a different person authorise financial records?
- Do rules differ by transaction type or amount?
- Do Pastor and Administrator have identical authorisation rights?

Source:
- domain_model.md, Section 9
- role_permissions.md
- finance_workflow.md, Section 11

### OD-10 — Rejected Financial Record Resubmission

Status: OPEN

Decision:
Confirm whether Rejected financial records may be edited
and resubmitted.

Questions:
- Which fields may be edited?
- Does resubmission return the record to Pending?
- Is a new authorisation decision required?
- How is the original rejection history preserved?

Source:
- finance_workflow.md, Section 4.5
- finance_workflow.md, Section 11

### OD-11 — Financial Correction and Reversal Policy

Status: OPEN

Decision:
Confirm the financial correction and reversal limits.

Questions:
- What adjustment types are permitted?
- What limits apply to partial and full reversals?
- What rules prevent excessive cumulative reversal?
- Are additional approval requirements needed?
- Which correction reasons are required?

Source:
- architecture.md, Section 16
- domain_model.md, Section 9
- finance_workflow.md, Sections 5 and 11

### OD-12 — Financial Reporting Policy

Status: OPEN

Decision:
Confirm remaining financial reporting rules.

Questions:
- What policy governs combined monthly income subtotals?
- Which financial export formats are required for Release 1?
- Are additional report-access or generation audit events required?

Source:
- finance_workflow.md, Sections 7 and 11

### OD-13 — Audit Retention and Archival

Status: OPEN

Decision:
Approve audit retention, archival, and secure disposal requirements.

Questions:
- How long must member audit records be retained?
- How long must attendance audit records be retained?
- How long must financial audit records be retained?
- What archival and disposal rules apply?
- What backup retention and access controls are required?

Source:
- audit_policy.md, Section 10
- audit_policy.md, Section 12
- architecture.md, Section 16

### OD-14 — Audit Access and Review

Status: OPEN

Decision:
Confirm general audit-log access and audit-review responsibilities.

Questions:
- May Pastor access general audit logs?
- Which audit events may each role review?
- Who is responsible for audit review?
- Are audit exports required?

Source:
- audit_policy.md, Sections 7, 8, and 12
- role_permissions.md

### OD-15 — Deployment Provider

Status: OPEN

Decision:
Confirm the production deployment provider.

Questions:
- Which hosting provider will be used?
- Which production environment configuration is required?
- What operational responsibilities apply?

Source:
- architecture.md, Section 16
- deployment.md

### OD-16 — Media Storage Provider

Status: OPEN

Decision:
Confirm the production media storage provider.

Questions:
- Where will uploaded media be stored?
- What access controls are required?
- What retention and backup requirements apply?

Source:
- architecture.md, Section 16
- deployment.md

### OD-17 — Performance and Operational Targets

Status: OPEN

Decision:
Define measurable performance and operational targets.

Questions:
- What response-time targets apply?
- What availability target is required?
- What monitoring and alerting requirements apply?
- What capacity and performance expectations apply to reports?

Source:
- architecture.md, Sections 16 and 17
- database_design.md, Section 17

## 4. Settled Domain Decisions

The following decisions are established in the current domain
and database documentation. They must not be treated as unresolved
unless the responsible owner formally reopens them.

### SD-01 — Visitor Count Categories

Status: PROPOSED RELEASE 1 DOMAIN DESIGN

Visitor counts use two supported categories:

- FIRST_TIME: First-time visitors
- RETURNING: Returning visitors

Rules:
- Counts are non-negative integers.
- Each attendance session may have one record per category.
- Visitor records remain aggregate-only.
- Individual visitor profiles are outside Release 1.
- Session total is the sum of FIRST_TIME and RETURNING counts.
- Missing category data is distinct from a recorded zero.

Source:
- domain_model.md, Sections 4 and 8
- database_design.md, Section 8.3

### SD-02 — Financial Record Lifecycle

Status: PROPOSED RELEASE 1 DOMAIN DESIGN

Financial records use:
- Pending
- Authorised
- Rejected

Authorised source records are immutable in place.
Corrections use linked, auditable adjustments.
Only authorised source records and authorised adjustments
contribute to confirmed financial totals.

Source:
- domain_model.md, Section 6
- finance_workflow.md, Sections 4 and 5

### SD-03 — Financial Role Access

Status: PROPOSED RELEASE 1 PERMISSION DESIGN

Financial access is limited to Pastor and Administrator.

Zone Leader and Public Visitor have no financial access.

Backend permission enforcement is required.

Source:
- role_permissions.md
- finance_workflow.md, Section 3

## 5. Decision Approval Record

Approved decisions must be recorded with:

- Decision ID
- Final decision
- Approval date
- Responsible decision owner
- Affected documentation
- Implementation impact

Until this information is recorded, the decision remains
unapproved.

## 6. Review

Review this register before:
- Finalising the Release 1 implementation baseline
- Implementing unresolved business rules
- Preparing production deployment

The register must remain consistent with:
- architecture.md
- domain_model.md
- database_design.md
- role_permissions.md
- finance_workflow.md
- audit_policy.md
