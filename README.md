<p align="center">
  <img src="frontend/icon.png" alt="tactile3d logo" width="200" />
</p>


# tactile3d

![tactile3d.png](tactile3d.png)
The ultimate CAD analysis and update platform.

## System Architecture (Mermaid)

```mermaid
flowchart LR
  %% Client
  subgraph Client["Client: Nextjs + Wallet"]
    U["CAD Engineer"]
    FE["Nextjs Web App"]
    W["Wallet (wagmi + viem)"]
    U --> FE
    W --> FE
  end

  %% Platform API
  subgraph API["Platform API (Spring Boot)"]
    REST[REST Controllers]
    WS[WebSocket Events]
    JOBS[Job Service]
    FILES[File Service]
    MEM[Memory Service]
    EVENTS[Agent Event Service]
  end

  %% Data layer
  subgraph Data["MongoDB"]
    DB[("Collections: users, jobs, results, memories")]
    GRID[("GridFS: CAD files + artifacts")]
  end

  %% Agent Module
  subgraph Agent["Agent Module (FastAPI)"]
    AAPI[Agent API]
    PARSE[PARSE]
    ANALYZE[ANALYZE]
    SUGGEST[SUGGEST]
    VALIDATE[VALIDATE]
  end

  %% External services
  subgraph Ext["External Services"]
    GH[GitHub OAuth]
    FW[Fireworks AI]
    VY[Voyage Embeddings]
    TH[Thesys C1]
    CDP["Coinbase CDP x402"]
  end

  %% Client <-> API
  FE -->|REST| REST
  FE -.->|WebSocket job updates| WS
  FE -->|x402 payment request| REST
  REST <-->|OAuth login| GH

  %% API internals
  REST --> JOBS
  REST --> FILES
  REST --> MEM
  REST --> EVENTS
  JOBS --> DB
  MEM --> DB
  EVENTS --> DB
  FILES --> GRID

  %% Agent orchestration
  REST <-->|start/resume/cancel| AAPI
  AAPI -->|fetch CAD via /api/files| FILES
  AAPI -.->|callbacks: checkpoint/complete/fail| REST
  AAPI --> PARSE --> ANALYZE --> SUGGEST --> VALIDATE

  %% AI + Payments
  MEM -->|embed| VY
  MEM -->|RAG answer| FW
  AAPI -->|DFM LLM assist| FW
  REST -->|UI spec from report| TH
  REST -->|verify/settle payments| CDP
```

## How to Use

1. Export your CAD design as a `.step` file in Fusion 360.
2. Upload the `.step` file to the platform.
3. Let the AI agents analyze and critique your design for DFM and performance.
4. Update your design based on the AI's suggestions.
5. Repeat steps 2-4 until your design is optimized.
6. Chat with the AI to get more insights and suggestions.
7. Generate a report of your design's DFM and performance.

## Tech Stack

- Frontend: Nextjs (Vercel) + TailwindCSS + Shadcn UI
- Backend: Spring Boot + MongoDB + GridFS + WebSocket
- AI: FastAPI + PARSE + Fireworks AI + Voyage Embeddings + Thesys C1
- Payments: Coinbase CDP x402
- Authentication: GitHub OAuth
