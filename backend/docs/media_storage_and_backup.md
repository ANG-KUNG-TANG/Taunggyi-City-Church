# Media Storage, Security, and Backup Guide

## 1. Purpose

This document describes the storage configuration, upload restrictions, access control, backup considerations, and restoration procedures for media uploaded to Activities and Announcements in the Taunggyi City Church Community Management System.

The media system supports images, videos, and PDF documents associated with Activities and Announcements.

## 2. Supported Media Types and Upload Limits

The following upload policy applies to both Activities and Announcements.

| Category | Supported Formats | Maximum File Size |
|---|---|---:|
| Images | JPEG, PNG, WebP | 10 MB |
| Videos | MP4, WebM | 100 MB |
| Documents | PDF | 20 MB |

The backend validates uploaded files using content-based checks rather than relying exclusively on filename extensions or client-provided MIME types.

Additional validation includes:

- Image parsing and format verification.
- Image pixel-count limits to reduce decompression-bomb risks.
- MP4 file signature verification.
- WebM EBML signature verification.
- PDF header verification.
- Empty-file and unsupported-format rejection.
- Filename sanitization.

These checks provide basic file-format validation. They do not constitute complete media-file parsing or malware scanning.

## 3. Storage Configuration

### 3.1 Local Development Storage

The default storage backend is Django's `FileSystemStorage`.

The current configuration in `config/settings/base.py` uses:

- `MEDIA_ROOT`: `BASE_DIR / "media"`
- `MEDIA_URL`: `/media/`
- `MEDIA_STORAGE_BACKEND`: `django.core.files.storage.FileSystemStorage`

The storage backend is configured through Django's `STORAGES` setting.

### 3.2 Environment Configuration

The `.env.example` file contains the following setting:

```env
MEDIA_STORAGE_BACKEND=django.core.files.storage.FileSystemStorage
```

The backend defaults to `FileSystemStorage` when this environment variable is not provided.

A different Django-compatible storage backend can be configured through `MEDIA_STORAGE_BACKEND` when production infrastructure is ready.

### 3.3 Production Storage

Production deployments must use persistent storage.

The deployment environment may use:

- Persistent server storage, or
- A compatible private object-storage backend.

The selected storage solution must preserve the application's access-control requirements. Media files must not become publicly accessible merely because they are stored in a production storage service.

Storage credentials and other sensitive configuration must be supplied through environment variables or an appropriate secrets-management mechanism. They must not be committed to source control.

## 4. Media Access Control

Media access is governed by the publication status of its associated Activity or Announcement.

### 4.1 Unpublished Content

For draft or archived content:

- Only authenticated Pastor and Admin users may retrieve the associated media through the media file endpoint.
- Anonymous users must not access unpublished media.
- Zone Leaders must not access unpublished media through the protected endpoint.

### 4.2 Published Content

Media associated with published Activities or Announcements may be accessed publicly.

The application checks the associated content's publication status before allowing file access.

### 4.3 Upload and Deletion Restrictions

Media uploads and deletions are restricted to authorized Pastor and Admin users.

Uploads and deletions are permitted only while the associated Activity or Announcement is in the DRAFT state.

Once the parent content is published or archived, media uploads and deletions through the management endpoints are rejected.

### 4.4 Direct Storage Access

Production web-server and object-storage configurations must not bypass application-level media authorization.

Do not expose the local `MEDIA_ROOT` directory through an unrestricted public static-file configuration.

Media should be delivered through the application's protected media file endpoint unless an equivalent access-controlled production mechanism has been implemented.

## 5. Backup Strategy

Media files and their associated database records must be backed up together.

A database-only backup is insufficient because it may preserve media metadata while losing the underlying files.

### 5.1 Required Backup Components

A complete backup should include:

1. The PostgreSQL database, including media metadata and relationships.
2. The media storage contents.
3. Relevant deployment configuration required to restore the storage backend.

Secrets and credentials must be handled separately and securely.

### 5.2 Backup Consistency

Database and media backups should represent a consistent recovery point.

For local filesystem storage, coordinate the database backup and media-file backup using an appropriate maintenance window or snapshot strategy.

For object storage, use the provider's supported backup, versioning, or snapshot capabilities where available.

### 5.3 Backup Security

Backups should:

- Be encrypted at rest and during transfer.
- Be accessible only to authorized personnel.
- Be stored separately from the primary application environment.
- Be protected against accidental deletion and unauthorized modification.
- Be checked periodically for integrity and completeness.

The project owner must approve the backup frequency and retention period before production deployment.

## 6. Restoration Procedure

A restoration should recover both database records and the corresponding media files.

Recommended restoration sequence:

1. Prepare the target application environment.
2. Configure the required database and media storage settings.
3. Restore the PostgreSQL database.
4. Restore the corresponding media files or object-storage snapshot.
5. Verify that restored media records reference available files.
6. Run Django system checks.
7. Test access to representative published and unpublished media.
8. Confirm that application-level authorization remains effective.

Restoration should be tested periodically in a non-production environment.

A successful database restoration alone does not establish that media restoration is complete.

## 7. Deletion and Retention

Media deletion is restricted to authorized Pastor and Admin users while the associated content remains in DRAFT state.

When a media record is deleted through the application, the database operation and audit event are handled by the media service. Physical file cleanup is managed after successful transaction completion by the configured Django cleanup integration.

Deleting a parent Activity or Announcement also cascades to its associated media records.

The following policies still require project-owner approval:

- The retention period for media files.
- The retention period for backups containing deleted media.
- Any legal or organizational requirements for retaining church-related records.

No fixed retention duration is defined in this document.

## 8. Operational Limitations and Future Improvements

The current implementation provides format checks and access control, but the following capabilities are not established as implemented:

- Malware and virus scanning.
- Complete structural validation of MP4 and WebM files.
- Complete PDF document validation.
- Automated backup scheduling.
- Automated backup-integrity verification.
- A tested production disaster-recovery process.
- A finalized production storage provider.

These capabilities should be evaluated before production deployment.

## 9. Production Readiness Checklist

- [ ] Select and configure persistent production media storage.
- [ ] Confirm that storage access cannot bypass application authorization.
- [ ] Configure secure storage credentials.
- [ ] Define backup frequency and retention periods.
- [ ] Implement database and media backup procedures.
- [ ] Verify backup integrity.
- [ ] Perform a restoration test.
- [ ] Evaluate malware-scanning requirements.
- [ ] Review media access and deletion permissions.
- [ ] Document the final production storage configuration.

