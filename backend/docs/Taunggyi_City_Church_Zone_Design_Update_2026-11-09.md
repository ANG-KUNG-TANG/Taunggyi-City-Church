# Taunggyi City Church — Zone Design Update

**Document:** OOAD / System Design
**Update date:** 9 November 2026
**Status:** Implemented Zone functionality; one assignment policy remains unresolved
**Source baseline:** `Taunggyi_City_Church_OOAD_System_Design.pdf` — Consolidated Release 1 Design, 4 November 2026

---

## 1. Confirmed clarification

A Zone may have **multiple Zone Leaders**. Zone Leader assignments are represented as separate assignment records rather than a single `zone.leader_id` field.

This clarification updates the existing design's `ZoneLeaderAssignment` relationship and implementation notes. It preserves the established role boundaries:

- Pastor manages zones and assigns Zone Leaders.
- Zone Leaders access member and attendance data only for zones to which they have an active assignment.
- Zone Leaders cannot manage zone assignments or transfer members between zones.
- Assignment changes must be attributable and retain historical records.

The implemented Zone module follows this assignment-based relationship.

## 2. Updated relationship

```text
User 1 ─── * ZoneLeaderAssignment * ─── 1 Zone
```

A Zone can have multiple active assignment records, one for each assigned Zone Leader.

The assignment table is the source of truth for current and historical leader-to-zone relationships.

### 2.1 ZoneLeaderAssignment

| Field | Type | Requirement |
|---|---|---|
| `id` | UUID | Primary key; generated |
| `user_id` | FK → `User` | Required; assigned staff user |
| `zone_id` | FK → `Zone` | Required; assigned zone |
| `assigned_by_id` | FK → `User` | Required; Pastor who made the assignment |
| `effective_from` | DateTime | Required; assignment effective start |
| `effective_to` | DateTime, nullable | Null indicates an assignment that has not ended |
| `created_at` | DateTime | Required; server timestamp |

The implementation uses `effective_from` and `effective_to` as the assignment date fields.

### 2.2 Assignment rules

1. Multiple Zone Leaders may be actively assigned to the same Zone.
2. An assignment is currently active when `effective_from <= now` and `effective_to IS NULL`.
3. Ending an assignment updates its end time; it does not delete the historical record.
4. Pastor is the actor permitted to create or end Zone Leader assignments.
5. Zone Leader authorization is derived from assignment records and checked server-side.
6. The system does not rely on a single leader field on `Zone`.
7. A unique active `(user_id, zone_id)` assignment prevents duplicate active assignment records for the same user and zone.
8. Historical assignment records are retained.

The implementation supports multiple active leaders per Zone and prevents duplicate active assignments for the same leader and Zone.

## 3. Scope enforcement

For a Zone Leader request, the backend verifies that the requested Zone is within the user's active assignment scope.

The implemented Zone API applies assigned-zone filtering to Zone Leader access.

The assignment-based authorization model is intended to support the following zone-scoped operations:

- Member list, detail, create and edit.
- Zone-specific attendance sessions and member attendance.
- Visitor counts and zone reports.
- Nested routes, exports and endpoints accepting zone, member or session identifiers.

A client-supplied `zone_id` is not authorization. The backend must validate the user's assignment before permitting access to zone-scoped resources.

Zone Leaders cannot transfer members between zones.

**Implementation boundary:** The current Zone module establishes Zone access and assignment scope. The full member, attendance, visitor-count, report and export enforcement requirements remain dependent on their respective modules and must be verified separately. The Zone implementation alone does not establish that every future endpoint is protected.

## 4. Implemented Zone API

The Zone API is registered under:

`/api/v1/zones/`

### 4.1 Zone endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/zones/` | List zones accessible to the requesting user |
| POST | `/api/v1/zones/` | Create a Zone |
| GET | `/api/v1/zones/{zone_id}/` | Retrieve a Zone |
| PATCH | `/api/v1/zones/{zone_id}/` | Partially update a Zone |
| PUT | `/api/v1/zones/{zone_id}/` | Replace a Zone using required fields |
| POST | `/api/v1/zones/{zone_id}/deactivate/` | Deactivate a Zone |

### 4.2 Zone Leader assignment endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/zones/{zone_id}/leaders/` | List Zone Leader assignments |
| POST | `/api/v1/zones/{zone_id}/leaders/` | Create a Zone Leader assignment |
| POST | `/api/v1/zones/{zone_id}/leaders/{assignment_id}/end/` | End an assignment |

These endpoints follow the implemented URL conventions.

Assignment-ending is implemented as `POST`, not `PATCH`.

### 4.3 Zone update behavior

`PATCH` supports partial updates.

`PUT` requires both `name` and `description`.

A PUT request missing either required field is rejected with a validation error.

The Zone model currently includes:

- UUID primary key
- Unique Zone name
- Description
- Active status
- Creation timestamp
- Update timestamp

The current implementation does **not** include a Zone `code` field.

A stable unique Zone code is therefore not part of the implemented model.

## 5. Open decision — can one Zone Leader serve multiple Zones?

The clarification confirms **multiple leaders per Zone**, but it does not confirm whether the **same Zone Leader may be assigned to more than one Zone simultaneously**.

Until church leadership confirms this policy:

- Keep the many-to-many assignment model.
- Do not add a database constraint limiting a user to one active Zone.
- Prevent duplicate active assignments for the same `(user_id, zone_id)` pair.
- Retain assignment history.
- Keep the cross-zone assignment policy documented as unresolved.

The current implementation permits the same Zone Leader to be assigned to multiple Zones.

If church leadership later requires one Zone per Zone Leader, introduce a conditional database constraint and corresponding service validation for active assignments.

This policy must be confirmed before introducing a restriction.

## 6. Implementation status

### 6.1 Completed Zone functionality

The following Zone functionality has been implemented:

- [x] Zone model and database migration.
- [x] Zone Leader assignment model with assignment history.
- [x] Model registration through the existing Django application structure.
- [x] Pastor-only Zone management.
- [x] Pastor-only Zone Leader assignment management.
- [x] Zone Leader assigned-zone access restrictions.
- [x] Multiple Zone Leaders assigned to one Zone.
- [x] Duplicate active assignment prevention.
- [x] Assignment-ending operation with historical retention.
- [x] Zone serializers and validation.
- [x] Zone API endpoints.
- [x] Service-level tests.
- [x] API-level tests.
- [x] Role permission tests.
- [x] Django system checks.
- [x] Migration consistency checks.

### 6.2 Verification results

The following verification was completed:

| Verification | Result |
|---|---|
| Focused Zone API tests | 18 passed |
| Complete backend test suite | 72 passed |
| Django system check | Passed; no issues identified |
| Migration consistency check | No changes detected |
| `git diff --check` | Passed |

The test suite reported 18 staticfiles warnings because the configured staticfiles directory was not present. These warnings did not cause test failures.

### 6.3 Remaining work

The following items remain outside the completed Zone implementation or require further confirmation:

- [ ] Confirm whether one Zone Leader may serve multiple Zones simultaneously.
- [ ] Verify assigned-zone enforcement across member APIs.
- [ ] Verify assigned-zone enforcement across attendance APIs.
- [ ] Verify assigned-zone enforcement across visitor-count operations.
- [ ] Verify assigned-zone enforcement across reports and exports.
- [ ] Confirm whether a stable Zone code is required by church leadership.
- [ ] Complete and verify cross-module authorization tests as the relevant modules are implemented.

These items must not be described as completed solely because the Zone module has passed its tests.

## 7. Design decisions and implementation notes

The existing design already includes `ZoneLeaderAssignment` and describes User–Zone relationships through that table.

This update makes the confirmed cardinality explicit:

**One Zone → Many Zone Leaders**

The implementation uses assignment records to represent current and historical relationships.

The current implementation also supports a Zone Leader serving multiple Zones, but this remains an unresolved church policy rather than a confirmed business requirement.

The Zone API uses the project's implemented route conventions. Assignment-ending is performed through a POST endpoint.

The current Zone model does not contain a `code` field. Any requirement to introduce a stable Zone code must be confirmed and handled as a separate model change.

The implementation has passed the available backend tests and Django validation checks. Future member, attendance, visitor-count and reporting modules must independently enforce the assignment-based authorization model.

---

**Change summary**

This update records the confirmed multiple-leader-per-Zone clarification and aligns the design document with the implemented Zone model, assignment fields, API endpoints and verification results.

It distinguishes completed Zone functionality from future cross-module authorization work and preserves the unresolved policy concerning whether one Zone Leader may serve multiple Zones simultaneously.
