---
title: SaaS-Ops OpenEnv Simulation
emoji: 📊
colorFrom: blue
colorTo: teal
sdk: docker
pinned: false
tags:
  - openenv
  - simulation
  - reinforcement-learning
  - saas
---

# SaaS-Ops OpenEnv Simulation

A B2B SaaS operations simulator built for the OpenEnv specification. An AI agent acts as
the startup COO — balancing feature development, marketing investment, and technical debt
across three increasingly difficult scenarios.

## Architecture

```
saas-ops/
├── models.py          # Pydantic schemas — Action, Observation, DebtDetail
├── core.py            # Math engine — SaaSState, step(), stochastic events
├── tasks.py           # Task graders — EasyTask, MediumTask, HardTask
├── server.py          # FastAPI app — /reset, /step, /state
├── baseline_agent.py  # LLM-powered baseline (Claude Haiku)
├── mock_agent.py      # Random agent for smoke-testing
├── openenv.yaml       # OpenEnv manifest
├── requirements.txt   # Python dependencies
└── Dockerfile         # Container definition
```

## Action Space

| Field         | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| `action_type` | string  | `"hire_dev"`, `"pay_debt"`, or `"marketing_push"` |
| `amount`      | float   | Rs. amount for `pay_debt` or `marketing_push`    |
| `count`       | integer | Number of devs to hire (for `hire_dev`)          |

## Observation Space

| Field                | Type    | Description                                  |
|----------------------|---------|----------------------------------------------|
| `cash`               | float   | Current cash in Rs.                          |
| `devs`               | int     | Active developers                            |
| `features_completed` | int     | Cumulative features shipped                  |
| `monthly_revenue`    | float   | Current MRR in Rs.                           |
| `tech_debt`          | float   | Tech debt score 0.0 (clean) – 1.0 (critical) |
| `tech_debt_details`  | object  | Reasoning, impact, and recommendation        |
| `current_month`      | int     | Month number (1-indexed after first step)    |
| `is_bankrupt`        | bool    | True if cash ≤ 0                             |
| `event_message`      | string? | Stochastic event description, or null        |

## Tasks

### Easy — Tech Debt Cleanup
- **Start**: Rs.20,000 cash, 80% tech debt, 2 devs
- **Goal**: Reduce tech debt to ≤ 40% before going bankrupt
- **Reward**: Partial progress signal proportional to debt reduction each step

### Medium — Revenue Generation
- **Start**: Rs.50,000 cash, 10% tech debt, 1 dev, Rs.0 MRR
- **Goal**: Reach Rs.10,000 Monthly Recurring Revenue
- **Reward**: `current_revenue / 10,000` each step (capped at 1.0)

### Hard — The Pivot Survival
- **Start**: Rs.30,000 cash, 40% tech debt, 3 devs, Rs.2,000 MRR
- **Goal**: Survive 12 months AND ship at least 12 pivot features
- **Reward**: Combined survival + feature progress signal each step

## Stochastic Events (15% chance per month)

| Event              | Effect                                    |
|--------------------|-------------------------------------------|
| Key dev quit       | −1 dev, +5% debt                          |
| Viral spike        | +Rs.3,000 revenue, +3% debt (load rush)   |
| Server outage      | −Rs.2,000 cash, −Rs.1,500 revenue         |
| Investor interest  | +Rs.5,000 cash                            |
| Bug flood          | −Rs.2,000 revenue, +8% debt               |

## Running Locally

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

Run the random smoke-test agent:
```bash
python mock_agent.py
```

Run the LLM baseline agent (requires `ANTHROPIC_API_KEY`):
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python baseline_agent.py
```

## Docker / Hugging Face Deployment

```bash
docker build -t saas-openenv .
docker run -p 8000:8000 saas-openenv
```

For Hugging Face Spaces, push this repo with the YAML front-matter above intact.
The Space will detect `sdk: docker` and build from the `Dockerfile` automatically.

## API Reference

| Endpoint       | Method | Body / Params            | Description                      |
|----------------|--------|--------------------------|----------------------------------|
| `/reset`       | POST   | `?task_level=easy`       | Resets env, returns initial obs  |
| `/step`        | POST   | `Action` JSON body       | Advances one month               |
| `/state`       | GET    | —                        | Returns current observation      |

### Example session

```bash
# Reset to medium task
curl -X POST "http://localhost:8000/reset?task_level=medium"

# Take a marketing action
curl -X POST "http://localhost:8000/step" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "marketing_push", "amount": 5000}'
```
