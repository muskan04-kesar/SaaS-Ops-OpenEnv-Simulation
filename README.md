---
tags: [openenv]
---

# SaaS-Ops OpenEnv Simulation

Welcome to the SaaS-Ops environment! This is an officially compliant OpenEnv simulation built for AI Agents. It simulates the operations of a B2B SaaS platform where the AI must balance feature development, marketing pushes, and critical technical debt.

## Architecture

This backend serves the environment entirely via a REST API.

- **`models.py`**: Contains the strictly typed Pydantic models mapping the Action Space, Observation State, and Rewards.
- **`core.py`**: The mathematical simulation handling resource allocation, diminishing developer productivity, and revenue burn.
- **`tasks.py`**: Deterministic Task Graders evaluating the exact conditions necessary for the agent to achieve "Task Success".
- **`server.py`**: A FastAPI application standardizing the interactions via `/reset` and `/step`.

## Tasks

Three distinct scenarios are tested:
1. **Easy (`easy`)**: Budgeted technical debt cleanup.
2. **Medium (`medium`)**: A 0 to 10k MRR sprint.
3. **Hard (`hard`)**: Complete pivot and survival over 12 intensive months.

## Running the Project

You can run the interactive HTTP API by installing the pip dependencies:
```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

Alternatively, build and run via Docker using the provided `Dockerfile`:
```bash
docker build -t saas-openenv .
docker run -p 8000:8000 saas-openenv
```
