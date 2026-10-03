# AI based ControlPlane — Manufacturing Control & Quality Management Platform

> **Enterprise-grade manufacturing operations platform for assembly-line process control, control-plan versioning, document intelligence, maintenance management, paint inspection, quality analytics, and real-time factory operations.**

ControlPlane is a full-stack manufacturing management platform designed to centralize **assembly-line processes, stations, control plans, document versions, operational workflows, maintenance faults, quality inspections, auditability, and production analytics** in a single system.

The platform combines a **FastAPI backend**, **Vue 3 frontend**, **PostgreSQL/Prisma data layer**, real-time WebSocket/SSE communication, document processing, OCR, monitoring, Docker-based deployment, and automated CI/CD.

---

## What Problem Does It Solve?

Manufacturing operations often depend on spreadsheets, manually maintained control plans, disconnected maintenance records, and limited visibility into process changes.

ControlPlane provides a centralized operational layer where teams can:

- Manage assembly lines and stations
- Manage manufacturing processes
- Upload and version control plans
- Compare control-plan revisions
- Detect document changes automatically
- Extract metadata and OCR text from documents
- Track missing control plans
- Migrate processes between stations
- Manage production workers and assignments
- Maintain an immutable audit history
- Manage maintenance faults and comments
- Perform paint-quality inspections
- Analyze defects and repair rates
- Monitor system/API health
- Receive real-time operational updates

---

# Core Capabilities

## 1. Manufacturing Process Management

ControlPlane models manufacturing operations around:

```text
Line
 └── Station
      └── Process
           └── Control Plan Versions
```

The system supports:

- Assembly line management
- Station management
- Process creation and lifecycle management
- Car-model association
- Process assignment
- Automatic process-code generation
- Active/archived states
- Missing control-plan detection
- Full-text process search
- Pagination and filtering

Example process code:

```text
TRIM-S01-P04
```

---

## 2. Control-Plan Version Management

Control plans can be uploaded as new versions while preserving their history.

Each version stores:

- Version identifier
- Original file
- File metadata
- Uploading user
- Commit message
- Change count
- Extracted metadata
- Version diff
- Creation timestamp
- Soft-delete/restore state

The system supports:

```text
Upload Version
      ↓
Store Document
      ↓
Extract Metadata
      ↓
Compare With Previous Version
      ↓
Generate Diff
      ↓
Persist Results
      ↓
Publish Real-Time Event
      ↓
Audit Action
```

This provides Git-like version control concepts for manufacturing control-plan documents.

---

# 3. Intelligent Excel Diff Engine

One of the core engineering components is the custom Excel comparison engine.

Instead of performing only a simple file-level comparison, the platform can analyze XLSX documents at multiple levels:

- Worksheets
- Rows
- Cells
- Groups
- Sub-operations
- Added values
- Removed values
- Modified values
- Structural changes

The engine supports different comparison strategies depending on workbook structure.

### Example

```text
Control Plan v1
      │
      │
      ▼
   Excel Diff
      │
      ├── Added: 3
      ├── Modified: 7
      └── Removed: 1
      │
      ▼
Control Plan v2
```

Diff results can also be used to generate highlighted Excel documents showing changes visually.

---

# 4. OCR & Document Intelligence

The backend includes document metadata extraction and OCR processing.

Supported processing includes:

- Spreadsheet metadata extraction
- Embedded image extraction
- OCR processing using Tesseract
- Text extraction
- Document structure analysis
- Metadata persistence
- Searchable process content

OCR is particularly useful for manufacturing documents where important information may exist inside embedded images rather than standard spreadsheet cells.

Technology:

```text
Python
Pillow
Tesseract / pytesseract
OpenPyXL
Pandas
```

---

# 5. Asynchronous Processing

Expensive document-processing operations are handled asynchronously so API requests do not need to wait for the entire diff pipeline.

Example:

```text
User Upload
     │
     ▼
API Response
     │
     └──────────────► Background Processing
                           │
                           ├── Download previous version
                           ├── Parse workbook
                           ├── OCR / metadata extraction
                           ├── Calculate diff
                           ├── Persist results
                           └── Publish status
```

The frontend receives processing-state updates through SSE/WebSockets.

---

# 6. Real-Time Communication

ControlPlane supports real-time operational events using:

- WebSockets
- Server-Sent Events (SSE)

Example events include:

```text
process.version.uploaded
process.diff.completed
process.version.restored
migration.completed
migration.failed
station.created
station.deleted
user.status.changed
```

AI/document-processing status can also transition through:

```text
idle
  ↓
ai_running
  ↓
completed
```

or:

```text
ai_running
     ↓
   failed
```

This allows the UI to update without requiring continuous polling.

---

# 7. Process Migration

Manufacturing processes can be migrated between stations and assembly lines.

The migration workflow supports:

- Source line/station
- Destination line/station
- Multiple processes
- Validation
- Migration status
- Asynchronous processing
- Migration history
- Audit records
- Real-time status events

Example:

```text
Trim Line / Station 01
          │
          │ Migration
          ▼
Chassis Line / Station 03
```

Every migration is tracked for operational traceability.

---

# 8. Maintenance Management

The platform includes a dedicated maintenance module for factory operations.

Features include:

- Maintenance authentication
- Maintenance users
- Fault management
- Fault severity
- Fault status
- Fault comments
- Maintenance dashboard
- Maintenance analytics
- Role-based access control
- Separate maintenance security context

Fault workflows can be managed independently from the primary manufacturing process-management workflow.

---

# 9. Paint Quality Inspection

ControlPlane also includes a dedicated paint-inspection module.

The inspection workflow supports:

- Vehicle inspection records
- Vehicle parts
- Defect tracking
- Defect types
- Paint colors
- Repair quantities
- Let-go quantities
- Inspection history
- Inspection detail views
- Defect aggregation
- Quality analytics

### Analytics include:

- Total inspections
- Total defects
- Average defects per inspection
- Total repaired
- Total let-go
- Overall repair rate
- Inspections by color
- Defects by type
- Defects by vehicle part
- Repair-rate analysis
- Inspection trends over time

---

# 10. Interactive Quality Dashboard

The frontend provides visual quality analytics using Chart.js.

Dashboard visualizations include:

```text
Defects by Type
        │
        ├── Bar Chart
        │
Repair vs Let Go
        │
        ├── Doughnut Chart
        │
Inspections by Color
        │
        ├── Pie Chart
        │
Defects by Vehicle Part
        │
        ├── Bar Chart
        │
Inspection Trends
        │
        └── Line Chart
```

This provides production teams with a visual overview of quality performance.

---

# 11. Audit & Traceability

ControlPlane maintains an immutable audit ledger for important system operations.

Tracked activities include:

- Uploads
- User actions
- Station changes
- Process changes
- Archives
- Migrations
- Model changes
- Version restoration
- Document-processing events

The audit system supports filtering by:

- Action type
- User
- Search term
- Date range
- Pagination

This provides traceability for operational and compliance workflows.

---

# 12. Role-Based Access Control

The platform implements role-based authorization.

Example roles include:

```text
Process Manager
Line Manager
Maintenance Admin
Maintenance Users
```

Permissions can determine access to:

- Processes
- Stations
- Assembly lines
- Control-plan uploads
- Migrations
- Car models
- Users
- Audit logs
- Maintenance operations

Authentication uses JWT-based security with password hashing.

---

# 13. Full-Text Search

The backend uses PostgreSQL full-text search for process documents.

The platform creates a PostgreSQL GIN index over searchable process content:

```text
Process
   │
   ├── Name
   ├── Code
   └── Extracted Search Text
            │
            ▼
     PostgreSQL FTS
            │
            ▼
       Fast Search
```

This provides more scalable document/process search than loading all records into application memory.

---

# 14. Production Observability

The application includes production monitoring using:

- Prometheus
- Grafana
- FastAPI instrumentation
- Custom user-level metrics
- API request metrics
- Status-code metrics
- Handler-level metrics
- Scheduled operational reports

Example metric:

```text
controlplane_user_requests_total
```

Monitoring architecture:

```text
FastAPI
   │
   ▼
Prometheus
   │
   ▼
Grafana
   │
   └── API / Operational Dashboards
```

---

# 15. Caching & Storage

The platform is designed around scalable infrastructure components including:

- PostgreSQL
- Redis
- S3-compatible object storage
- Application-level caching
- Persistent database metadata
- External document storage

Large control-plan files are separated from database metadata to support scalable file management.

---

# 16. API Architecture

The backend follows a modular service architecture:

```text
FastAPI
│
├── Routers
│
├── Controllers
│
├── Services
│
├── Schemas
│
├── Core
│
├── Helpers
│
├── Repositories
│
└── Database
```

API endpoints are grouped under:

```text
/api/v1
```

Major domains include:

```text
/auth
/users
/lines
/stations
/processes
/versions
/car-models
/migrations
/audit
/dashboard
/workers
/tools
/maintenance
/paint-inspection
/ws
```

OpenAPI documentation is automatically available through FastAPI.

---

# Technology Stack

## Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- Prisma
- SQLAlchemy
- PostgreSQL
- AsyncPG
- JWT
- bcrypt
- APScheduler

## Document & Data Processing

- OpenPyXL
- Pandas
- Pillow
- pytesseract
- Excel semantic diff engine
- PDF processing
- OCR

## Frontend

- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Tailwind CSS
- Chart.js
- Vue Chart.js
- VueUse
- Lucide icons

## Infrastructure

- Docker
- Docker Compose
- Nginx
- PostgreSQL
- Redis
- S3-compatible storage
- Prometheus
- Grafana

## Real-Time

- WebSockets
- Server-Sent Events
- Async background processing

## DevOps

- GitHub Actions
- Automated builds
- Docker deployment
- Environment-based configuration
- Linux deployment
- Cloudflare deployment workflows

---

# Architecture

```text
                         ┌──────────────────────┐
                         │      Vue 3 UI        │
                         │ TypeScript + Pinia   │
                         └──────────┬───────────┘
                                    │
                              REST / SSE / WS
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     FastAPI API      │
                         │     /api/v1          │
                         └──────────┬───────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      Process Services       Maintenance Module     Paint Inspection
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
                PostgreSQL        Redis       Object Storage
                    │
                    ▼
             Audit / Versions
                    │
                    ▼
           Document Processing
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
      Excel Diff              OCR
          │                   │
          └─────────┬─────────┘
                    ▼
              Processing Result
                    │
                    ▼
              SSE / WebSocket
                    │
                    ▼
                  UI
```

---

# Repository Structure

```text
control_management/
│
├── backend/
│   ├── app/
│   │   ├── controllers/
│   │   ├── core/
│   │   ├── helpers/
│   │   ├── maintenance/
│   │   ├── paint_inspection/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── sse/
│   │   └── websocket/
│   │
│   ├── prisma/
│   ├── grafana/
│   ├── prometheus/
│   ├── nginx/
│   ├── Dockerfile
│   └── docker-compose.yml
│
└── frontend/
    ├── src/
    │   ├── components/
    │   ├── composables/
    │   ├── layouts/
    │   ├── modules/
    │   │   ├── maintenance/
    │   │   └── paint-inspection/
    │   ├── services/
    │   ├── stores/
    │   └── views/
    │
    ├── public/
    ├── Dockerfile
    └── package.json
```

---

# Security

Security controls include:

- JWT authentication
- Password hashing with bcrypt
- Role-based authorization
- Separate maintenance authentication context
- Protected WebSocket connections
- Protected API routes
- Environment-based secrets
- File validation
- Upload size restrictions
- Audit logging
- Soft-delete workflows
- Input validation through Pydantic schemas

---

# Deployment

The application supports containerized deployment.

```text
Docker Compose
      │
      ├── Backend
      ├── Frontend
      ├── PostgreSQL
      ├── Redis
      ├── Nginx
      ├── Prometheus
      └── Grafana
```

Production configuration is controlled through environment variables.

CI/CD workflows are included for:

- Backend builds
- Frontend builds
- Docker workflows
- Deployment
- Restart operations
- Environment-specific deployment

---

# Running Locally

## Backend

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API:

```text
http://localhost:8000
```

Swagger/OpenAPI:

```text
http://localhost:8000/docs
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

## Docker

```bash
cd backend

docker compose up -d --build
```

---

# API Documentation

FastAPI automatically exposes:

```text
/docs
/redoc
```

The repository also includes detailed frontend/API documentation.

---

# Engineering Highlights

This project demonstrates practical experience in:

- Enterprise backend architecture
- Full-stack application development
- Async Python
- REST API design
- Database modeling
- Document processing
- OCR
- Excel parsing and semantic comparison
- Version control concepts
- Real-time systems
- WebSocket/SSE architecture
- Background processing
- RBAC
- Security
- Auditability
- Manufacturing workflows
- Quality management
- Production monitoring
- Containerization
- CI/CD
- Scalable infrastructure

---

# Project Focus

```text
Manufacturing Operations
        +
Process Control
        +
Document Intelligence
        +
Quality Management
        +
Maintenance
        +
Real-Time Operations
        +
Production Observability
```

ControlPlane is designed as an operational platform rather than a simple CRUD application, with emphasis on **traceability, version control, asynchronous processing, real-time communication, security, and production deployment**.

---

## License

Add your preferred license here.

---

## Author

**Awais Saeed**

Senior Software Engineer | AI/ML | Python Backend | Full-Stack Systems

GitHub: `https://github.com/OWAIS086-web`
