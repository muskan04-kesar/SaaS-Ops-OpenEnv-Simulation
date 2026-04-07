import os
import json
import httpx
import asyncio
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load key from .env if present
load_dotenv()

# Configuration from environment variables as per hackathon requirements
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("GROQ_API_KEY")

# The environment's internal REST API (FastAPI)
# Port 7860 as defined in Dockerfile and openenv.yaml
SIMULATOR_URL = "http://localhost:7860"

# Initialize OpenAI client
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN
)

SYSTEM_PROMPT = """You are an expert SaaS startup COO. Each month you must choose exactly one action.

Available actions:
- hire_dev        : Hire developers. Each costs Rs.2,000 upfront + Rs.5,000/month salary.
- pay_debt        : Spend money to reduce technical debt. Rs.20,000 clears 100% of debt.
- marketing_push  : Spend money on marketing to grow monthly revenue.

Respond ONLY with valid JSON — no extra text, no markdown fences:
{
  "action_type": "hire_dev" | "pay_debt" | "marketing_push",
  "amount": <number>,
  "count": <integer>,
  "reasoning": "<one sentence explaining your decision>"
}"""

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

async def ask_llm(observation: dict, task_level: str) -> dict:
    """Send the current observation to the LLM and get an action back."""
    user_message = f"""Task: {task_level.upper()}
Current state:
- Month       : {observation['current_month']}
- Cash        : Rs.{observation['cash']:,.0f}
- Devs        : {observation['devs']}
- Tech Debt   : {observation['tech_debt'] * 100:.0f}%
- Monthly Rev : Rs.{observation['monthly_revenue']:,.0f}
- Features    : {observation['features_completed']}
- Bankrupt    : {observation['is_bankrupt']}
- Event       : {observation.get('event_message') or 'None this month'}

What action do you take this month?"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=256,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response.choices[0].message.content.strip()

        # Clean JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        
        return json.loads(raw)
    except Exception as e:
        # Fallback action on failure
        return {"action_type": "pay_debt", "amount": 2000, "count": 0, "reasoning": f"Fallback: {e}"}

async def run_task(task_level: str, max_steps: int = 12):
    log_start(task=task_level, env="saas-ops-sim", model=MODEL_NAME)
    
    rewards = []
    steps_taken = 0
    success = False
    score = 0.0
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Reset
            resp = await http_client.post(f"{SIMULATOR_URL}/reset", params={"task_level": task_level})
            resp.raise_for_status()
            data = resp.json()
            obs = data["observation"]
            
            for step in range(1, max_steps + 1):
                action_dict = await ask_llm(obs, task_level)
                action_type = action_dict.get("action_type", "pay_debt")
                
                # Step
                resp = await http_client.post(f"{SIMULATOR_URL}/step", json=action_dict)
                resp.raise_for_status()
                result = resp.json()
                
                obs = result["observation"]
                reward = result["reward"]
                done = result["done"]
                
                rewards.append(reward)
                steps_taken = step
                
                log_step(step=step, action=action_type, reward=reward, done=done, error=None)
                
                if done:
                    break
            
            # Simple score normalization (example: sum of rewards capped at 1.0)
            total_reward = sum(rewards)
            score = max(0.0, min(1.0, total_reward / 10.0)) 
            success = score >= 0.5 or (not obs['is_bankrupt'] and task_level == 'easy' and obs['tech_debt'] <= 0.4)

    except Exception as e:
        print(f"[DEBUG] Error in task {task_level}: {e}")
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    
    return score

async def main():
    # Sequence of tasks for the hackathon
    for level in ["easy", "medium", "hard"]:
        await run_task(level)

if __name__ == "__main__":
    asyncio.run(main())
