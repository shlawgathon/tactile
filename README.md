<p align="center">
  <img src="frontend/icon.png" alt="tactile3d logo" width="200" /><br />
  <br />
  <i>The ultimate multi-agent orchestrated CAD analysis and update platform.</i>
</p>

# tactile3d

![tactile3d.png](tactile3d.png)

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
    PARTSAPI["/api/parts (x402)"]
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
    PARTS["Parts Search"]
    X402C["x402 Client"]
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
  PARTS -->|GET /api/parts/search| PARTSAPI
  X402C -->|GET /cad + X-PAYMENT| PARTSAPI
  PARTSAPI -->|verify/settle| CDP
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

- Frontend: Nextjs (Vercel) + TailwindCSS
- Backend: Spring Boot + MongoDB + GridFS + WebSocket
- AI: FastAPI + PARSE + Fireworks AI + Voyage Embeddings + Thesys C1
- Payments: Coinbase CDP x402
- Authentication: GitHub OAuth

## x402 Agent Payments

The CAD agent supports autonomous payments for external x402-protected services using the Coinbase x402 protocol on **Base Sepolia testnet** (no real funds required).

**Features:**

- **Budget Control** - Set spending limit before upload via popup
- **Parts Search** - Search for screws, bearings, motors during chat
- **Automatic Payment** - Agent signs x402 payments for premium CAD data

### Parts API Endpoints

| Endpoint                          | Auth     | Description                     |
| --------------------------------- | -------- | ------------------------------- |
| `GET /api/parts/search?query=...` | None     | Search parts catalog (free)     |
| `GET /api/parts/{partNumber}`     | None     | Get part details (free)         |
| `GET /api/parts/{partNumber}/cad` | **x402** | Download CAD (requires payment) |

### Available MOCK Parts Catalog

| Part Number     | Name                            | Price (test USDC) |
| --------------- | ------------------------------- | ----------------- |
| `MC-M3X10-SHCS` | M3 x 10mm Socket Head Cap Screw | $0.01             |
| `MC-MR63ZZ`     | MR63ZZ Miniature Ball Bearing   | $0.02             |
| `NEMA17-42`     | NEMA 17 Stepper Motor           | $0.05             |
| `LM8UU`         | LM8UU Linear Ball Bearing       | $0.01             |

### x402 Payment Flow

```
Agent → GET /api/parts/MC-M3X10-SHCS/cad
     ← 402 Payment Required (price: $0.01 USDC)
Agent → Signs payment with wallet (Base Sepolia)
Agent → GET /cad + X-PAYMENT header
     → Backend verifies via CDP Facilitator API
     → Backend settles payment
     ← 200 OK + CAD data + transaction hash
```

**Setup:**

```bash
cd agent
pip install -e .
python -m tools.x402_client  # Generate wallet
# Fund at: https://faucet.cdp.coinbase.com/
```

Add to `.env`:

```
X402_AGENT_PRIVATE_KEY=0x...
X402_NETWORK=base-sepolia
```

Powered by [CadQuery](https://cadquery.readthedocs.io/en/latest/apireference.html#id1) - Python library for controlling parametric 3D CAD models
