# PLAN.md - Tactile: Long-Running CAD Analysis Platform

> MongoDB AI Agents Hackathon - Statement One: Prolonged Coordination

---

## 1. Executive Summary

**Project Name**: Tactile  
**Tagline**: "Long-running CAD analysis that doesn't quit"

A platform that performs multi-hour CAD analysis jobs using AI agents. Users upload STEP/CAD files, select a manufacturing process, and receive detailed DFM (Design for Manufacturing) feedback with suggested fixes. The system persists state through MongoDB, enabling graceful recovery from failures and modification of tasks mid-execution.

### Why CadQuery as the AI Mutation Layer?

- **LLMs already understand Python** - Research shows 69%+ accuracy on Text-to-CadQuery generation
- **Executable = Verifiable** - Run the generated code, check if geometry is valid
- **Pure Python** - No external CAD software dependencies
- **B-Rep Output** - Generates real STEP files, not meshes

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js on Vercel)                     │
│         Upload UI  ·  Job Tracker  ·  Results Viewer  ·  3D Preview      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST + WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PLATFORM API (Java Spring Boot)                       │
│                                                                          │
│  • OAuth2 Authentication (Google, GitHub)                                │
│  • User Management & Permissions                                         │
│  • Job CRUD & Queue Management                                           │
│  • File Storage (GridFS or S3)                                           │
│  • Checkpoint/State Persistence                                          │
│  • WebSocket Hub for Real-time Updates                                   │
│  • Billing & Usage Tracking                                              │
│                                                                          │
│  Endpoints:                                                              │
│    POST   /api/jobs              - Create analysis job                   │
│    GET    /api/jobs/{id}         - Get job status                        │
│    DELETE /api/jobs/{id}         - Cancel job                            │
│    GET    /api/jobs/{id}/results - Get analysis results                  │
│    POST   /api/jobs/{id}/resume  - Resume failed job                     │
│    WS     /ws/jobs/{id}          - Real-time job updates                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP Callbacks + Message Queue
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AGENT MODULE (Python)                               │
│                                                                          │
│  • Receives jobs from Platform API                                       │
│  • Runs CadQuery analysis pipeline                                       │
│  • Checkpoints state back to Platform API                                │
│  • Returns results on completion                                         │
│                                                                          │
│  Pipeline Stages:                                                        │
│    1. PARSE    - Load STEP, extract geometry info                        │
│    2. ANALYZE  - Run DFM checks against rules                            │
│    3. SUGGEST  - Generate fix recommendations                            │
│    4. VALIDATE - Verify suggested fixes produce valid geometry           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         MONGODB ATLAS                                    │
│                                                                          │
│  Collections: users, jobs, checkpoints, results, dfm_rules              │
│  Features: Vector Search for similar issues, Change Streams for         │
│            real-time updates, GridFS for file storage                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Responsibilities

### 3.1 Frontend (Next.js + Vercel)

**Purpose**: User-facing interface for upload, monitoring, and results viewing.

**Features**:
- Drag-and-drop STEP file upload
- Manufacturing process selection (Injection Molding, CNC, 3D Printing)
- Real-time job progress via WebSocket
- 3D model preview using Three.js
- Issue list with severity highlighting
- Suggested fix viewer with before/after comparison
- User dashboard with job history

**Tech Stack**: Next.js 14, React, Three.js, TailwindCSS, shadcn/ui

---

### 3.2 Platform API (Java Spring Boot)

**Purpose**: Central orchestration layer handling auth, storage, and job coordination.

**Responsibilities**:
- OAuth2 authentication (Spring Security)
- User account management and permissions
- Job lifecycle management (create, track, cancel, resume)
- File upload and storage (MongoDB GridFS or S3)
- Checkpoint persistence from Agent Module
- WebSocket server for real-time job updates
- Rate limiting and usage quotas
- Webhook notifications on job completion

**Key Integrations**:
- MongoDB Atlas (primary database)
- Agent Module (HTTP/message queue communication)
- Voyage AI (embeddings for similar issue search)
- Email/Slack notifications

**Communication with Agent Module**:
- Platform API sends job request to Agent Module via HTTP POST or message queue
- Agent Module periodically sends checkpoint data back via HTTP callback
- On completion, Agent Module sends final results to Platform API
- Platform API stores everything and notifies frontend via WebSocket

---

### 3.3 Agent Module (Python)

**Purpose**: Performs the actual CAD analysis using CadQuery and LLMs.

**Responsibilities**:
- Receive job payloads from Platform API
- Execute multi-stage analysis pipeline
- Send checkpoint data to Platform API after each stage
- Use LLM (Fireworks AI) for enhanced issue descriptions and suggestions
- Generate CadQuery code for suggested fixes
- Validate fixes produce valid geometry
- Return structured results to Platform API

**Pipeline Stages**:

1. **PARSE** - Load STEP file into CadQuery, extract geometry metadata (faces, edges, volume, bounding box)

2. **ANALYZE** - Run DFM rule checks based on selected manufacturing process, identify issues

3. **SUGGEST** - Generate recommendations and CadQuery fix code using LLM

4. **VALIDATE** - Execute suggested CadQuery code, verify resulting geometry is valid

**Checkpoint Strategy**:
- After each stage completes, POST checkpoint to Platform API
- Checkpoint includes: current stage, intermediate results, reasoning trace
- On failure, Platform API can request resume from last checkpoint

---

## 4. Data Models

### 4.1 User
```
User {
  id: UUID
  email: String
  name: String
  oauth_provider: String (google, github)
  oauth_id: String
  created_at: Timestamp
  subscription_tier: String (free, pro, enterprise)
  usage_this_month: Integer
}
```

### 4.2 Job
```
Job {
  id: UUID
  user_id: UUID
  status: Enum (QUEUED, PARSING, ANALYZING, SUGGESTING, VALIDATING, COMPLETED, FAILED, CANCELLED)
  
  // Input
  original_filename: String
  file_storage_id: String (GridFS or S3 key)
  manufacturing_process: Enum (INJECTION_MOLDING, CNC_MACHINING, FDM_3D_PRINTING)
  material: String (optional)
  
  // Progress
  current_stage: String
  progress_percent: Integer
  stages_completed: List<String>
  
  // Timing
  created_at: Timestamp
  started_at: Timestamp
  completed_at: Timestamp
  
  // Error handling
  error_message: String
  retry_count: Integer
  last_checkpoint_id: UUID
  
  // Results summary (populated on completion)
  total_issues: Integer
  critical_issues: Integer
  warnings: Integer
}
```

### 4.3 Checkpoint
```
Checkpoint {
  id: UUID
  job_id: UUID
  stage: String
  stage_index: Integer
  
  state: JSON (serialized agent state)
  reasoning_trace: List<String>
  intermediate_results: JSON
  
  created_at: Timestamp
  is_recoverable: Boolean
}
```

### 4.4 AnalysisResult
```
AnalysisResult {
  id: UUID
  job_id: UUID
  
  // Geometry summary
  bounding_box: JSON
  volume: Double
  surface_area: Double
  face_count: Integer
  edge_count: Integer
  
  // Issues found
  issues: List<Issue>
  issues_by_severity: Map<String, Integer>
  
  // Suggestions
  suggestions: List<Suggestion>
  generated_code_snippets: List<CodeSnippet>
  
  // Output files
  modified_step_file_id: String (optional)
  preview_image_ids: List<String>
  
  created_at: Timestamp
}
```

### 4.5 Issue
```
Issue {
  rule_id: String
  rule_name: String
  severity: Enum (ERROR, WARNING, INFO)
  description: String
  affected_features: List<String> (face/edge IDs)
  recommendation: String
  auto_fix_available: Boolean
}
```

### 4.6 Suggestion
```
Suggestion {
  issue_id: String
  description: String
  expected_improvement: String
  priority: Integer (1-5)
  code_snippet: String (CadQuery code)
  validated: Boolean
}
```

### 4.7 DFMRule (for vector search)
```
DFMRule {
  id: String
  name: String
  process: String
  category: String (wall_thickness, draft, undercut, etc.)
  description: String
  parameters: JSON
  severity: String
  embedding: Vector (Voyage AI)
}
```

---

## 5. CadQuery Integration

### 5.1 Core Operations

The Agent Module uses CadQuery for all geometry operations:

**Loading STEP Files**:
```python
import cadquery as cq

workplane = cq.importers.importStep("part.step")
```

**Extracting Geometry Info**:
```python
solid = workplane.val()
bbox = solid.BoundingBox()
volume = solid.Volume()
faces = workplane.faces().vals()
edges = workplane.edges().vals()
```

**Analyzing Faces for Draft**:
```python
for face in faces:
    normal = face.normalAt(face.Center())
    # Calculate angle relative to pull direction
```

**Generating Fixes (Fillet Example)**:
```python
result = workplane.edges("|Z").fillet(0.5)
```

**Validating Geometry**:
```python
if result.val().Volume() > 0:
    # Geometry is valid
```

**Exporting**:
```python
cq.exporters.export(result, "output.step", exportType="STEP")
cq.exporters.export(result, "preview.stl", exportType="STL")
```

### 5.2 Analysis Functions Needed

- `analyze_wall_thickness(workplane)` → min, max, avg, thin regions
- `analyze_draft_angles(workplane, pull_direction)` → faces needing draft
- `detect_undercuts(workplane, pull_direction)` → undercut faces
- `analyze_overhangs(workplane)` → faces exceeding 45° (for 3D printing)
- `detect_sharp_corners(workplane, min_radius)` → edges needing fillets
- `analyze_holes(workplane)` → hole dimensions, depth ratios

---

## 6. DFM Rules Reference

### 6.1 Injection Molding

| Rule | Threshold | Severity |
|------|-----------|----------|
| Minimum wall thickness | 0.8mm | Error |
| Maximum wall thickness | 4.0mm | Warning |
| Wall thickness uniformity | ±25% variation | Warning |
| Minimum draft angle | 0.5° (1-2° recommended) | Error |
| Textured surface draft | +1° per 0.025mm texture | Warning |
| Rib thickness | 50-70% of wall | Warning |
| Rib height | Max 3x rib thickness | Warning |
| Internal corner radius | Min 0.5mm | Warning |

### 6.2 CNC Machining

| Rule | Threshold | Severity |
|------|-----------|----------|
| Internal corner radius | Min = tool radius (typically 1.5mm) | Error |
| Pocket depth | Max 3x tool diameter | Warning |
| Minimum wall thickness | 0.8mm metal, 1.5mm plastic | Error |
| Hole depth | Max 10x diameter | Warning |
| Standard hole sizes | Use standard drill sizes | Info |

### 6.3 FDM 3D Printing

| Rule | Threshold | Severity |
|------|-----------|----------|
| Overhang angle | Max 45° from vertical | Warning |
| Bridge length | Max 5mm without support | Warning |
| Minimum wall thickness | 0.8mm (2x nozzle) | Error |
| Minimum feature size | 0.4mm (nozzle diameter) | Error |

---

## 7. Sponsor Integration

### 7.1 MongoDB Atlas

**Usage**:
- Primary database for all collections
- GridFS for STEP file storage
- Vector Search for finding similar past issues and relevant DFM rules
- Change Streams for real-time job status updates to WebSocket

**Vector Search Index** on `dfm_rules.embedding` for semantic rule lookup.

### 7.2 Voyage AI

**Usage**:
- Embed DFM rules for semantic search
- Embed issue descriptions to find similar past issues
- Model: `voyage-3` (1024 dimensions)
- Free tier: 200M tokens (plenty for hackathon)

### 7.3 Fireworks AI

**Usage**:
- LLM inference for enhanced issue descriptions
- Generate human-readable recommendations
- Produce CadQuery fix code
- Model: `llama-v3p1-70b-instruct`

### 7.4 Vercel

**Usage**:
- Host Next.js frontend
- Edge functions for API proxying if needed

### 7.5 NVIDIA NeMo Agent Toolkit (Optional)

**Usage**:
- If time permits, use for multi-agent orchestration
- Could have specialized agents debate fix approaches

---

## 8. Checkpoint & Recovery Flow

### 8.1 Normal Execution

```
1. Platform API receives job request
2. Platform API creates Job record (status: QUEUED)
3. Platform API sends job to Agent Module
4. Agent Module executes PARSE stage
5. Agent Module POSTs checkpoint to Platform API
6. Platform API saves checkpoint, updates job status
7. Agent Module executes ANALYZE stage
8. Agent Module POSTs checkpoint to Platform API
9. ... repeat for SUGGEST and VALIDATE ...
10. Agent Module POSTs final results to Platform API
11. Platform API saves results, updates job (status: COMPLETED)
12. Platform API notifies frontend via WebSocket
```

### 8.2 Failure Recovery

```
1. Agent Module fails during ANALYZE stage
2. Agent Module catches exception, POSTs error to Platform API
3. Platform API updates job (status: FAILED, error_message: ...)
4. Platform API has last good checkpoint from PARSE stage

Later (manual or automatic retry):
5. Platform API calls POST /api/jobs/{id}/resume
6. Platform API sends job to Agent Module with checkpoint data
7. Agent Module loads checkpoint, skips PARSE, resumes from ANALYZE
8. ... continues normally ...
```

### 8.3 Task Modification Mid-Execution

```
1. User changes manufacturing_process while job is in ANALYZE
2. Frontend calls PATCH /api/jobs/{id} with new parameters
3. Platform API updates job, marks current work as invalidated
4. Platform API signals Agent Module to restart from PARSE
5. Agent Module receives restart signal, begins fresh analysis
```

---

## 9. API Contracts

### 9.1 Platform API → Agent Module

**Start Job**:
```json
POST /agent/jobs/start
{
  "job_id": "uuid",
  "file_url": "https://...",
  "manufacturing_process": "INJECTION_MOLDING",
  "material": "ABS",
  "callback_url": "https://platform-api/internal/jobs/{id}/callback",
  "resume_from_checkpoint": null
}
```

**Resume Job**:
```json
POST /agent/jobs/start
{
  "job_id": "uuid",
  "file_url": "https://...",
  "manufacturing_process": "INJECTION_MOLDING",
  "callback_url": "https://platform-api/internal/jobs/{id}/callback",
  "resume_from_checkpoint": {
    "stage": "PARSE",
    "state": { ... },
    "intermediate_results": { ... }
  }
}
```

### 9.2 Agent Module → Platform API

**Checkpoint**:
```json
POST /internal/jobs/{id}/checkpoint
{
  "stage": "ANALYZE",
  "stage_index": 2,
  "state": { ... },
  "reasoning_trace": ["Started analysis", "Checking draft angles", ...],
  "intermediate_results": { "issues_found": 3 },
  "is_recoverable": true
}
```

**Completion**:
```json
POST /internal/jobs/{id}/complete
{
  "success": true,
  "results": {
    "geometry_summary": { ... },
    "issues": [ ... ],
    "suggestions": [ ... ],
    "generated_code": [ ... ]
  },
  "output_files": {
    "modified_step": "base64...",
    "preview_stl": "base64..."
  }
}
```

**Failure**:
```json
POST /internal/jobs/{id}/fail
{
  "error_message": "CadQuery failed to load STEP file",
  "error_type": "PARSE_ERROR",
  "recoverable": false
}
```

---

## 10. Implementation Timeline

### Day 1 (Hours 1-8)

**Hour 1-2**: Project setup
- Initialize repos (platform-api, agent-module, frontend)
- Set up MongoDB Atlas cluster
- Configure environment variables

**Hour 3-4**: Platform API foundation
- Spring Boot project with MongoDB connection
- Basic Job CRUD endpoints
- File upload to GridFS

**Hour 5-6**: Agent Module foundation
- Python project with CadQuery
- STEP file loading and basic geometry extraction
- Simple HTTP server for receiving jobs

**Hour 7-8**: Integration
- Platform API → Agent Module communication
- Basic checkpoint flow
- Test end-to-end with simple STEP file

### Day 2 (Hours 9-16)

**Hour 9-10**: DFM Analysis
- Implement core analysis functions (draft, thickness, overhangs)
- Add rules for one manufacturing process (start with 3D printing)

**Hour 11-12**: LLM Integration
- Integrate Fireworks AI for enhanced descriptions
- Generate human-readable suggestions

**Hour 13-14**: Frontend basics
- Upload interface
- Job status display
- Results viewer

**Hour 15-16**: Polish & Demo Prep
- WebSocket real-time updates
- Error handling
- Demo script preparation

---

## 11. File Structure

```
Tactile/
├── platform-api/                    # Java Spring Boot
│   ├── src/main/java/com/Tactile/
│   │   ├── config/                  # Security, MongoDB, WebSocket config
│   │   ├── controller/              # REST controllers
│   │   ├── service/                 # Business logic
│   │   ├── repository/              # MongoDB repositories
│   │   ├── model/                   # Entity classes
│   │   ├── dto/                     # Request/Response DTOs
│   │   └── websocket/               # WebSocket handlers
│   └── pom.xml
│
├── agent-module/                    # Python
│   ├── Tactile/
│   │   ├── cad/
│   │   │   ├── parser.py            # STEP loading, geometry extraction
│   │   │   ├── analyzer.py          # DFM analysis functions
│   │   │   └── codegen.py           # CadQuery code generation
│   │   ├── dfm/
│   │   │   ├── rules.py             # DFM rule definitions
│   │   │   └── checker.py           # Rule checking logic
│   │   ├── agents/
│   │   │   ├── base.py              # Base agent class
│   │   │   ├── parser_agent.py
│   │   │   ├── analyzer_agent.py
│   │   │   └── suggester_agent.py
│   │   ├── api/
│   │   │   └── server.py            # FastAPI server
│   │   └── integrations/
│   │       ├── fireworks.py         # LLM client
│   │       └── voyage.py            # Embeddings client
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                        # Next.js
│   ├── app/
│   │   ├── page.tsx                 # Landing/upload
│   │   ├── jobs/[id]/page.tsx       # Job detail/results
│   │   └── dashboard/page.tsx       # User dashboard
│   ├── components/
│   │   ├── FileUpload.tsx
│   │   ├── JobTracker.tsx
│   │   ├── ResultsViewer.tsx
│   │   └── ModelPreview.tsx         # Three.js viewer
│   └── package.json
│
└── README.md
```

---

## 12. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CadQuery installation issues | Use Docker container with pre-built environment |
| STEP file parsing failures | Validate file before processing, graceful error messages |
| LLM rate limits | Cache common responses, batch requests |
| Long analysis times | Progress updates via WebSocket, realistic time estimates |
| MongoDB connection issues | Connection pooling, retry logic |
| Agent Module crashes | Checkpoint after each stage enables resume |

---

## 13. Demo Script

1. **Upload** - Drag STEP file of a part with intentional DFM issues (missing draft, thin walls, overhangs)

2. **Configure** - Select "FDM 3D Printing" as manufacturing process

3. **Watch** - Show real-time progress as job moves through stages

4. **Results** - Display issues found with severity levels

5. **Suggestions** - Show recommended fixes with CadQuery code

6. **Recovery Demo** - Kill Agent Module mid-job, show resume from checkpoint

---

## 14. Success Criteria

- [ ] Upload STEP file and receive analysis results
- [ ] Job survives Agent Module restart (checkpoint/resume works)
- [ ] Real-time progress updates in frontend
- [ ] At least 5 DFM rules implemented with meaningful suggestions
- [ ] LLM-enhanced issue descriptions
- [ ] Clean demo flow under 5 minutes