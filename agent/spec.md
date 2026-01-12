# Agent Module Specification

## Overview

The Agent Module is a FastAPI-based Python service that performs CAD/DFM (Design for Manufacturing) analysis. It receives analysis requests from the Platform API, runs the analysis pipeline, and returns structured results.

---

## Architecture

```
agent/
├── main.py                 # FastAPI application entry point
├── models.py               # Pydantic request/response models
├── fireworks_client.py     # Fireworks AI LLM integration
├── report_generator.py     # Markdown report generation
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (gitignored)
│
└── cad_tool/               # CAD analysis pipeline
    ├── source.py           # CADTool main class
    ├── parse/              # STEP file parsing
    │   └── parser.py
    ├── analyze/            # DFM analysis modules
    │   ├── analyzer.py
    │   ├── geometry_analyzer.py
    │   ├── physical_analyzer.py
    │   ├── surface_analyzer.py
    │   └── assembly_analyzer.py
    ├── suggest/            # Fix suggestion generation
    │   └── suggester.py
    └── validate/           # Geometry validation
        └── validator.py
```

---

## API Endpoints

### `GET /health`

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "cad_analyzer_available": true,
  "fireworks_configured": true
}
```

### `POST /analyze`

Main DFM analysis endpoint.

**Request:**

```json
{
  "manufacturing_process": "INJECTION_MOLDING" | "CNC_MACHINING" | "FDM_3D_PRINTING",
  "cad_description": "Text description of the CAD model",
  "file_url": "https://...",
  "material": "ABS",
  "pull_direction": [0, 0, 1]
}
```

**Response:**

```json
{
  "success": true,
  "issues": [...],
  "suggestions": [...],
  "markdown_report": "# DFM Analysis Report\n..."
}
```

---

## Pipeline Stages

| Stage        | Module                           | Description                                   |
| ------------ | -------------------------------- | --------------------------------------------- |
| **PARSE**    | `cad_tool/parse/parser.py`       | Load STEP file, extract geometry metadata     |
| **ANALYZE**  | `cad_tool/analyze/`              | Run DFM checks against manufacturing rules    |
| **SUGGEST**  | `cad_tool/suggest/suggester.py`  | Generate fix recommendations + CadQuery code  |
| **VALIDATE** | `cad_tool/validate/validator.py` | Verify suggested fixes produce valid geometry |

---

## DFM Rules

### Injection Molding

- Min wall: 0.8mm, Max wall: 4.0mm
- Draft angle: ≥0.5° (recommend 1-2°)
- Rib thickness: 50-70% of wall
- Internal corner radius: ≥0.5mm

### CNC Machining

- Internal corner radius: ≥1.5mm
- Pocket depth: ≤3x tool diameter
- Hole depth: ≤10x diameter

### FDM 3D Printing

- Overhang angle: ≤45° without support
- Bridge length: ≤5mm
- Min wall: 0.8mm, Min feature: 0.4mm

---

## Environment Variables

| Variable                 | Required | Description                                  |
| ------------------------ | -------- | -------------------------------------------- |
| `FIREWORKS_API_KEY`      | Yes      | Fireworks AI API key                         |
| `PORT`                   | No       | Server port (default: 8001)                  |
| `X402_AGENT_PRIVATE_KEY` | No       | EVM private key for x402 payments            |
| `X402_NETWORK`           | No       | Network for payments (default: base-sepolia) |

---

## x402 Demand Side Payments

The agent can autonomously pay for external x402-protected services using stablecoins (USDC).

### How It Works

1. Agent makes HTTP request to an external x402-protected API
2. If 402 Payment Required is returned, the x402 client:
   - Parses payment requirements from response
   - Signs a payment authorization with the agent wallet
   - Retries the request with payment header
3. External service verifies and settles the payment
4. Agent receives the requested resource

### Creating an Agent Wallet

Generate a new wallet with Python:

```python
from eth_account import Account
acct = Account.create()
print(f"Address: {acct.address}")
print(f"Private Key: {acct.key.hex()}")
```

Or run: `python -m tools.x402_client`

Fund the wallet with test USDC: https://faucet.cdp.coinbase.com/

### Parts Search Tool

The agent has access to a `search_parts` tool that can search for components:

- **Fasteners**: screws, bolts, nuts, washers
- **Bearings**: ball bearings, linear bearings
- **Motors**: stepper motors, DC motors
- **Linear motion**: rails, lead screws

When connected to x402-enabled parts APIs, the agent can:

1. Search for parts by specification
2. Download CAD models (paid via x402)
3. Get detailed specifications

### Security Notes

- Use a **dedicated agent wallet** with limited funds
- Never use production user wallets
- Set spending limits in application logic
- Monitor wallet balance and transactions

---

## Running Locally

```bash
cd agent
pip install -e .  # Installs all dependencies including x402
uvicorn main:app --reload --port 8001
```

Docs: http://localhost:8001/docs
