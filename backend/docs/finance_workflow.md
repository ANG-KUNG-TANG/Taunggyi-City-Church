# Finance Workflow

## 1. Purpose and Scope

The Finance module manages donation records and daily fund transactions.

Only Pastor and Administrator may access financial records, financial
dashboards, financial reports, and financial APIs.

Zone Leaders and Public Visitors have no financial access.

The module supports:
- Donation and daily fund transaction entry
- Editing eligible financial records
- Authorisation and rejection
- Financial transaction history
- Correction and reversal
- Financial summaries and protected reports

This document describes the proposed Release 1 workflow.
Church-specific policy decisions remain subject to approval.

## 2. Financial Record Types

### 2.1 Donation

A donation record contains:
- Transaction date
- Positive amount
- Currency code
- Donation category
- Payment method
- Optional donor identity
- Anonymous donation indicator
- Optional notes
- Status
- Creation and update actor/timestamps
- Current authorisation actor/timestamp

Rules:
- Amount must be greater than zero.
- Currency is stored explicitly.
- Currency conversion is not assumed.
- Category must be active and have DONATION or BOTH scope.
- Anonymous donations must not store donor identity.
- Notes must not contain unnecessary sensitive information.
- Status is Pending, Authorised, or Rejected.

### 2.2 Fund Transaction

A fund transaction contains:
- Transaction date
- Positive amount
- Currency code
- Fund category
- Transaction type
- Optional notes
- Status
- Creation and update actor/timestamps
- Current authorisation actor/timestamp

Rules:
- Amount is stored as a positive absolute value.
- Income or expense direction is represented by transaction type.
- Currency is explicit; no implicit conversion is performed.
- Category must be active and have FUND or BOTH scope.
- Proposed transaction types are INCOME and EXPENSE.
- Status is Pending, Authorised, or Rejected.

## 3. Roles and Access

### Pastor
May:
- Create and edit financial records
- Authorise or reject financial records
- View financial dashboards and reports
- Review financial transaction history and audit history
- Create and review financial corrections and reversals

### Administrator
May:
- Create and edit financial records
- Authorise or reject financial records
- View financial dashboards and reports
- Review financial transaction history and audit history
- Create and review financial corrections and reversals

### Zone Leader and Public Visitor
Financial access is prohibited.

All financial permissions must be enforced by the backend.
Frontend visibility is not an access-control mechanism.

## 4. Financial Status Workflow

### 4.1 Create

1. Validate the transaction.
2. Create the financial record as Pending.
3. Record the actor and server timestamp.
4. Write the corresponding CREATE audit event.

### 4.2 Edit Pending Records

1. Verify the user has financial permission.
2. Verify the record is eligible for editing.
3. Update permitted fields.
4. Record the editor and timestamp.
5. Record redacted before/after values in the audit event.

### 4.3 Authorise

1. Verify the user has financial permission.
2. Verify the record is Pending.
3. Record the authorisation decision.
4. Update the record status to Authorised.
5. Store the decision and status update atomically.
6. Write the authorisation audit event.

Only Authorised source records contribute to confirmed financial totals.

### 4.4 Reject

1. Verify the user has financial permission.
2. Verify the record is Pending.
3. Record the rejection decision and reason.
4. Update the status to Rejected.
5. Write the rejection audit event.

Rejected records do not contribute to confirmed financial totals.

### 4.5 Rejected Record Resubmission

Editing and resubmitting a Rejected record is proposed.

If permitted:
1. Preserve the existing decision history.
2. Edit the eligible fields.
3. Return the record to Pending.
4. Require a fresh authorisation decision.

Whether rejected records may be edited and resubmitted requires
business approval.

### 4.6 Authorised Records

Authorised financial records are immutable in place.

An attempt to edit an Authorised record must:
- Leave the original unchanged
- Return HTTP 409 Conflict
- Direct the user to the correction/reversal workflow

## 5. Correction and Reversal

1. Locate the Authorised original Donation or FundTransaction.
2. Create a FinancialAdjustment linked to exactly one original transaction.
3. Record the adjustment type, signed amount delta, reason, creator,
   and timestamp.
4. Keep the original Authorised record unchanged.
5. Submit the adjustment as Pending.
6. Record a separate authorisation decision.
7. Only an Authorised adjustment affects confirmed financial totals.
8. Pending and Rejected adjustments do not affect confirmed totals.
9. Prevent cumulative reversals from exceeding the remaining net
   authorised amount.
10. Audit adjustment creation, editing, decision, and report-impacting
    actions.

A correction may use a positive or negative amount delta.
A full reversal negates the remaining net recognised amount.

Separation-of-duties policy remains unresolved.

## 6. Financial Authorisation History

FinancialAuthorization represents a decision event.

Each decision records:
- Decision identifier
- Exactly one target: donation, fund transaction, or adjustment
- Decision: AUTHORISE or REJECT
- Decision actor
- Decision timestamp
- Optional reason or comment
- Request correlation metadata

Decision rows are append-only.

The current status on the financial record is a projection of the latest
valid decision. The decision event is the historical record.

Every authorisation event must target exactly one financial record.

## 7. Financial Reporting

### 7.1 Daily Donation Report

Includes:
- Transaction date
- Donation amount
- Category
- Payment method
- Status
- Totals by currency

Pending, Rejected, and Authorised amounts must be shown separately.
Confirmed totals include Authorised records and Authorised adjustments.

### 7.2 Daily Fund Report

Includes fund transactions grouped by:
- Date
- Category
- Transaction type
- Currency
- Status

Income and expense must be separate.
Confirmed figures include Authorised records and Authorised adjustments.

### 7.3 Monthly Donation Report

Includes donations for the selected calendar month:
- Totals by category
- Currency grouping
- Status breakdown

### 7.4 Monthly Income Report

Shows Authorised fund income and donation income as separately
labelled components.

Currencies must not be mixed.
Any combined subtotal must follow approved policy.

### 7.5 Financial Transaction History

Shows chronological donation, fund transaction, and adjustment events.

The history includes:
- Created and updated actors
- Timestamps
- Decision history
- Correction and reversal references

### 7.6 Pending Authorisation Report

Includes Pending donations, fund transactions, and adjustments.

Supports review of pending records and their ageing.
Pending records are excluded from confirmed totals.

### 7.7 Authorised Financial Records

Provides read-only access to Authorised source records and Authorised
adjustments.

Original financial records remain immutable.

### 7.8 Date Range Summaries

Includes:
- Donations
- Fund income and expenses
- Adjustments
- Status breakdown

Confirmed totals include only Authorised records and Authorised
adjustments.

Date boundaries must use the configured timezone.

## 8. Calculation and Currency Rules

- Pending and Rejected values are never included in confirmed totals.
- Only Authorised source records and Authorised adjustments contribute
  to confirmed financial figures.
- Donation and fund totals must be calculated according to their
  respective transaction types.
- Reports must not mix currencies.
- Group totals by currency code unless an approved exchange-rate
  policy is introduced.
- Monthly income should show donation income and fund income as
  separately labelled components.
- Date ranges use inclusive selected local-date boundaries.
- Timezone interpretation must be configured and documented.
- Reports must avoid double counting adjustments.

## 9. Dashboard and Export Access

Pastor and Administrator may access:
- Donation and fund summaries
- Trends
- Pending authorisation counts
- Authorised totals
- Rejected totals
- Latest transaction activity

Dashboard data must come from protected backend endpoints.

Zone Leader financial dashboard requests must return 403 Forbidden.

PDF, Excel, and CSV exports are not confirmed for Release 1.

If exports are enabled, they must:
- Reuse backend permissions
- Reuse report calculation rules
- Include generation metadata
- Avoid public URLs

## 10. Audit Requirements

Financial audit events must record:

### CREATE
Actor, timestamp, entity identifier, amount, currency, category,
status, and permitted initial metadata.

### UPDATE
Actor, timestamp, and redacted before/after values for eligible
Pending or Rejected records.

### AUTHORISE / REJECT
Decision actor, timestamp, decision, reason, and target reference.

### ADJUST / REVERSE
Original transaction reference, signed delta, reason, actor,
timestamps, and later approval event.

### REPORT ACCESS
Where required by audit policy, record the user, report type,
requested date range, and generation time.

Ordinary application endpoints must not update or delete audit rows.
Database-level operational controls should restrict audit mutation.

## 11. Unresolved Business Decisions

The following require church leadership or project-owner approval:

- Whether creators may authorise their own financial records
- Separation-of-duties requirements
- Whether Rejected records may be edited and resubmitted
- Whether financial categories are configured by administrators
  or fixed in code
- Approved currency list
- Supported payment methods
- Transaction-date future-date policy
- Monthly income combined subtotal policy
- Financial report export formats for Release 1
- Financial and audit data retention requirements

Do not implement these decisions as confirmed policy until approved.

## 12. Source

Taunggyi City Church Community Management System
OOAD & System Design:
- Section 17: Donation and Fund Management Design
- Section 18: Financial Reporting and Audit Design

This document describes proposed Release 1 behavior.
It does not establish implementation or church-policy approval.
