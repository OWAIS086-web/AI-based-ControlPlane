# ControlPlane API Specification

A RESTful API design for the ControlPlane manufacturing assembly line management system.

## Conventions

- Base URL: `/api/v1`
- Auth: Bearer token (JWT) via `Authorization: Bearer <token>` header
- Dates: ISO 8601 (`2024-03-12T14:30:00Z`)
- Pagination: `?page=1&limit=20` (default limit: 20, max: 100)
- Filtering: query params (e.g. `?status=active&lineId=trim`)
- Errors follow [RFC 7807 Problem Details](https://datatracker.ietf.org/doc/html/rfc7807)

---

## Schemas

### Core Types

```ts
type Role = 'process_manager' | 'line_manager'
type UserStatus = 'active' | 'inactive'
type ProcessStatus = 'active' | 'archived'
type CarModelStatus = 'active' | 'archived'
type MigrationStatus = 'pending' | 'completed' | 'failed'
type AuditType = 'upload' | 'user' | 'station' | 'archive' | 'migrate' | 'model'
```

### Paginated Response Envelope

```ts
interface PaginatedResponse<T> {
  data: T[]
  meta: {
    total: number
    page: number
    limit: number
    totalPages: number
  }
}
```

### Error Response

```ts
interface ErrorResponse {
  type: string           // URI identifying the error type
  title: string          // Short human-readable summary
  status: number         // HTTP status code
  detail: string         // Detailed explanation
  instance?: string      // URI of the specific occurrence
  errors?: FieldError[]  // Validation errors (422 only)
}

interface FieldError {
  field: string
  message: string
}
```

---

## Entity Schemas

### User

```ts
interface User {
  id: string            // UUID
  name: string
  email: string
  role: Role
  status: UserStatus
  avatar: string | null // URL or initials fallback
  createdAt: string
  updatedAt: string
}
```

### Assembly Line

```ts
interface AssemblyLine {
  id: string            // e.g. "trim", "chassis"
  name: string
  icon: string
  color: string         // hex
  stationCount: number  // computed
  managerId: string | null  // User.id
  manager: User | null      // expanded on request
}
```

### Station

```ts
interface Station {
  id: string            // UUID
  name: string
  lineId: string        // AssemblyLine.id
  processCount: number  // computed
  createdAt: string
  updatedAt: string
}
```

### Car Model

```ts
interface CarModel {
  id: string            // UUID
  name: string
  code: string          // e.g. "CRL-2024"
  color: string         // hex
  status: CarModelStatus
  createdAt: string
  updatedAt: string
}
```

### Process

```ts
interface Process {
  id: string            // UUID
  name: string
  code: string          // e.g. "TRIM-S01-P03"
  lineId: string
  stationId: string
  carModelId: string
  status: ProcessStatus
  hasMissingCP: boolean
  versionCount: number  // computed
  latestVersion: ProcessVersion | null
  createdAt: string
  updatedAt: string
}
```

### Process Version

```ts
interface ProcessVersion {
  id: string            // UUID
  processId: string
  version: string       // e.g. "v1.0", auto-incremented
  fileUrl: string       // signed URL to stored file
  fileSize: number      // bytes
  commitMessage: string
  changes: number       // row-level diff count
  uploadedBy: string    // User.id
  uploader: User | null // expanded on request
  diff: DiffRow[]
  createdAt: string
}

interface DiffRow {
  row: string
  field: string
  oldValue: string
  newValue: string
}
```

### Migration Record

```ts
interface MigrationRecord {
  id: string            // UUID
  fromLineId: string
  fromStationId: string
  toLineId: string
  toStationId: string
  processIds: string[]
  status: MigrationStatus
  performedBy: string   // User.id
  createdAt: string
  completedAt: string | null
}
```

### Audit Entry

```ts
interface AuditEntry {
  id: string            // UUID
  type: AuditType
  action: string        // Human-readable description
  target: string        // Affected entity name/id
  performedBy: string   // User.id
  performer: User | null
  metadata: Record<string, unknown>  // Extra context per type
  createdAt: string
}
```

### Settings

```ts
interface UserSettings {
  userId: string
  notifications: {
    newUploads: boolean
    migrations: boolean
    userChanges: boolean
    systemAlerts: boolean
  }
  dataRetentionDays: number  // e.g. 30, 60, 90, 365
  updatedAt: string
}
```

---

## Endpoints

---

### Auth

#### `POST /auth/login`

Authenticate and receive a JWT.

**Request**
```json
{
  "email": "ahmad@factory.com",
  "password": "secret"
}
```

**Response `200`**
```json
{
  "accessToken": "<jwt>",
  "refreshToken": "<jwt>",
  "expiresIn": 3600,
  "user": { ...User }
}
```

**Errors:** `401` Invalid credentials, `422` Validation error

---

#### `POST /auth/refresh`

Exchange a refresh token for a new access token.

**Request**
```json
{ "refreshToken": "<jwt>" }
```

**Response `200`**
```json
{ "accessToken": "<jwt>", "expiresIn": 3600 }
```

---

#### `POST /auth/logout`

Revoke the current session.

**Response `204`** No content

---

### Users

> Requires `process_manager` role unless noted.

#### `GET /users`

List all users.

**Query params:** `?role=line_manager&status=active&page=1&limit=20`

**Response `200`** `PaginatedResponse<User>`

---

#### `POST /users`

Create a new user.

**Request**
```json
{
  "name": "Sara Ahmed",
  "email": "sara@factory.com",
  "role": "line_manager",
  "password": "temporary123"
}
```

**Response `201`** `User`

**Errors:** `409` Email already exists, `422` Validation error

---

#### `GET /users/:userId`

Get a single user.

**Response `200`** `User`

---

#### `PATCH /users/:userId`

Update user profile. Users may update their own profile; managers can update any.

**Request** *(all fields optional)*
```json
{
  "name": "Sara M. Ahmed",
  "email": "sara.ahmed@factory.com"
}
```

**Response `200`** `User`

---

#### `PATCH /users/:userId/status`

Activate or deactivate a user.

**Request**
```json
{ "status": "inactive" }
```

**Response `200`** `User`

---

#### `DELETE /users/:userId`

Permanently delete a user.

**Response `204`** No content

**Errors:** `409` Cannot delete user with active assignments

---

#### `GET /users/:userId/settings`

Get notification and retention settings. Users can access their own.

**Response `200`** `UserSettings`

---

#### `PATCH /users/:userId/settings`

Update settings. Users can update their own.

**Request** *(all fields optional)*
```json
{
  "notifications": {
    "newUploads": true,
    "migrations": false
  },
  "dataRetentionDays": 90
}
```

**Response `200`** `UserSettings`

---

### Assembly Lines

#### `GET /lines`

List all assembly lines with manager info.

**Response `200`**
```json
[{ ...AssemblyLine, "manager": { ...User } }]
```

---

#### `GET /lines/:lineId`

Get a single assembly line.

**Response `200`** `AssemblyLine`

---

#### `PATCH /lines/:lineId/manager`

Assign or remove the line manager. Requires `process_manager`.

**Request**
```json
{ "managerId": "user-uuid-here" }
```
Set `managerId` to `null` to unassign.

**Response `200`** `AssemblyLine`

**Errors:** `404` User not found, `422` User is not a line manager

---

### Stations

#### `GET /lines/:lineId/stations`

List all stations for a line.

**Query params:** `?page=1&limit=20`

**Response `200`** `PaginatedResponse<Station>`

---

#### `POST /lines/:lineId/stations`

Create a station. Requires `process_manager`.

**Request**
```json
{ "name": "Station 01" }
```

**Response `201`** `Station`

**Errors:** `409` Station name already exists on this line

---

#### `PATCH /lines/:lineId/stations/:stationId`

Rename a station. Requires `process_manager`.

**Request**
```json
{ "name": "Station 01 - Revised" }
```

**Response `200`** `Station`

---

#### `DELETE /lines/:lineId/stations/:stationId`

Delete a station. Requires `process_manager`.

**Response `204`** No content

**Errors:** `409` Station has active processes — archive or migrate them first

---

### Processes

#### `GET /processes`

Global process list with full filtering support.

**Query params:**
| Param | Type | Description |
|---|---|---|
| `lineId` | string | Filter by line |
| `stationId` | string | Filter by station |
| `carModelId` | string | Filter by car model |
| `status` | string | `active` \| `archived` |
| `hasMissingCP` | boolean | Missing control plan flag |
| `search` | string | Full-text on name/code |
| `page` | number | Page number |
| `limit` | number | Results per page |

**Response `200`** `PaginatedResponse<Process>`

---

#### `GET /lines/:lineId/stations/:stationId/processes`

List processes for a specific station.

**Query params:** `?status=active&carModelId=uuid&page=1`

**Response `200`** `PaginatedResponse<Process>`

---

#### `POST /lines/:lineId/stations/:stationId/processes`

Create a process. Requires `process_manager`.

**Request**
```json
{
  "name": "Door Panel Trim",
  "carModelId": "car-model-uuid"
}
```
The `code` is auto-generated from line/station/sequence (e.g. `TRIM-S01-P04`).

**Response `201`** `Process`

---

#### `GET /processes/:processId`

Get full process detail including latest version.

**Response `200`** `Process`

---

#### `PATCH /processes/:processId/status`

Archive or restore a process. Requires `process_manager`.

**Request**
```json
{ "status": "archived" }
```

**Response `200`** `Process`

---

### Process Versions

#### `GET /processes/:processId/versions`

List all versions for a process, newest first.

**Query params:** `?page=1&limit=20`

**Response `200`** `PaginatedResponse<ProcessVersion>`

---

#### `POST /processes/:processId/versions`

Upload a new control plan version. Requires `process_manager`. Multipart form.

**Request** `multipart/form-data`
| Field | Type | Description |
|---|---|---|
| `file` | File | Control plan file (CSV/XLSX, max 50MB) |
| `commitMessage` | string | Description of changes |

**Response `201`** `ProcessVersion`

The server:
1. Stores the file in object storage
2. Parses and diffs against the previous version
3. Auto-increments the version string
4. Sets `hasMissingCP = false` on the parent process
5. Writes an audit entry

**Errors:** `422` Invalid file type or size, `409` Upload already in progress

---

#### `GET /processes/:processId/versions/:versionId`

Get a single version with full diff.

**Response `200`** `ProcessVersion`

---

#### `GET /processes/:processId/versions/compare`

Compare two versions side-by-side.

**Query params:** `?v1=version-uuid&v2=version-uuid`

**Response `200`**
```json
{
  "v1": { ...ProcessVersion },
  "v2": { ...ProcessVersion },
  "diff": [{ "row": "...", "field": "...", "oldValue": "...", "newValue": "..." }],
  "summary": {
    "added": 3,
    "modified": 7,
    "removed": 1
  }
}
```

---

### Car Models

#### `GET /car-models`

List car models.

**Query params:** `?status=active&page=1`

**Response `200`** `PaginatedResponse<CarModel>`

---

#### `POST /car-models`

Create a car model. Requires `process_manager`.

**Request**
```json
{
  "name": "Yaris 2025",
  "code": "YRS-2025",
  "color": "#3B82F6"
}
```

**Response `201`** `CarModel`

**Errors:** `409` Code already exists

---

#### `PATCH /car-models/:modelId`

Update a car model. Requires `process_manager`.

**Request** *(all optional)*
```json
{
  "name": "Yaris 2025 Revised",
  "color": "#6366F1"
}
```

**Response `200`** `CarModel`

---

#### `PATCH /car-models/:modelId/status`

Archive or restore a car model. Requires `process_manager`.

**Request**
```json
{ "status": "archived" }
```

**Response `200`** `CarModel`

**Errors:** `409` Cannot archive — model has active processes

---

### Migrations

#### `GET /migrations`

List migration history.

**Query params:** `?status=completed&fromLineId=trim&page=1`

**Response `200`** `PaginatedResponse<MigrationRecord>`

---

#### `POST /migrations`

Migrate processes between stations. Requires `process_manager`.

**Request**
```json
{
  "fromLineId": "trim",
  "fromStationId": "station-uuid",
  "toLineId": "chassis",
  "toStationId": "station-uuid",
  "processIds": ["proc-uuid-1", "proc-uuid-2"]
}
```

**Response `202`** `MigrationRecord` with `status: "pending"`

Migrations are processed asynchronously. Poll `GET /migrations/:migrationId` or listen via WebSocket for status updates.

**Errors:** `404` Station or process not found, `422` Source and destination are the same, `409` Process already being migrated

---

#### `GET /migrations/:migrationId`

Get migration status and details.

**Response `200`** `MigrationRecord`

---

### Audit Log

#### `GET /audit`

Query the immutable audit ledger.

**Query params:**
| Param | Type | Description |
|---|---|---|
| `type` | string | `upload` \| `user` \| `station` \| `archive` \| `migrate` \| `model` |
| `performedBy` | string | User ID |
| `search` | string | Full-text on action/target |
| `from` | string | ISO date (start range) |
| `to` | string | ISO date (end range) |
| `page` | number | Page number |
| `limit` | number | Results per page |

**Response `200`** `PaginatedResponse<AuditEntry>`

---

#### `GET /audit/stats`

Aggregate counts per audit type for dashboard/filter badges.

**Response `200`**
```json
{
  "total": 148,
  "byType": {
    "upload": 42,
    "user": 18,
    "station": 9,
    "archive": 25,
    "migrate": 14,
    "model": 40
  }
}
```

---

## Dashboard

#### `GET /dashboard/stats`

Aggregated stats for the dashboard overview. Single efficient query.

**Response `200`**
```json
{
  "totalStations": 22,
  "totalProcesses": 148,
  "totalCarModels": 8,
  "missingCPCount": 5,
  "lines": [
    {
      "id": "trim",
      "name": "Trim Line",
      "stationCount": 5,
      "processCount": 31,
      "missingCPCount": 2,
      "managerId": "user-uuid"
    }
  ],
  "recentActivity": [ ...AuditEntry[] ] // last 10
}
```

---

## Real-Time Events (WebSocket)

Connect to `wss://api/v1/ws?token=<jwt>` to receive push events.

**Event envelope:**
```json
{
  "event": "migration.completed",
  "payload": { ...MigrationRecord },
  "timestamp": "2024-03-12T14:30:00Z"
}
```

**Events:**

| Event | Payload | Description |
|---|---|---|
| `migration.completed` | `MigrationRecord` | Async migration finished |
| `migration.failed` | `MigrationRecord` | Async migration failed |
| `process.version.uploaded` | `ProcessVersion` | New version available |
| `station.created` | `Station` | New station added |
| `station.deleted` | `{ stationId, lineId }` | Station removed |
| `user.status.changed` | `User` | User activated/deactivated |

---

## Access Control Matrix

| Resource | Process Manager | Line Manager (own lines) | Line Manager (other lines) |
|---|:---:|:---:|:---:|
| View dashboard | ✓ | ✓ | ✓ |
| View processes | ✓ | ✓ | ✗ |
| Upload versions | ✓ | ✗ | ✗ |
| Manage stations | ✓ | ✗ | ✗ |
| Migrate processes | ✓ | ✗ | ✗ |
| View audit log | ✓ | ✗ | ✗ |
| Manage users | ✓ | ✗ | ✗ |
| Manage car models | ✓ | ✗ | ✗ |
| View own settings | ✓ | ✓ | ✓ |
| Assign line manager | ✓ | ✗ | ✗ |

---

## Scalability Notes

- **Pagination** is enforced on all list endpoints to prevent unbounded queries.
- **Audit log** is append-only — never mutate entries; use a write-optimized table/partition.
- **File storage** — control plan files go to object storage (S3-compatible); only URLs/metadata in the DB.
- **Version diffing** — compute diffs asynchronously after upload; store results to avoid re-computation.
- **Migrations** — run asynchronously via a job queue (e.g. BullMQ); use the WebSocket event or poll for status.
- **Dashboard stats** — pre-aggregate with a materialized view or cache layer (Redis, 60s TTL) to avoid expensive joins on every page load.
- **Audit stats** — cache `GET /audit/stats` results, invalidated on each new audit write.
- **Rate limiting** — apply per-user limits on upload endpoints to prevent abuse.
- **Soft deletes** — all entities use `status` fields rather than hard deletes to preserve referential integrity and audit history.
