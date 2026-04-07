"""
baseline_agent.py
-----------------
LLM-powered baseline agent using Groq's free API (llama-3.1-8b-instant).

Setup:
    1. Sign up free at https://console.groq.com
    2. Create an API key (no credit card needed)
    3. pip install groq httpx
    4. export GROQ_API_KEY=your_key_here

Run (server must be running first):
    uvicorn server.app:app --host 0.0.0.0 --port 8000
    python baseline_agent.py
"""

import os
import json
import httpx
from groq import Groq
from dotenv import load_dotenv

# Load key from .env
load_dotenv()

BASE_URL = "http://localhost:8000"
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are an expert SaaS startup COO. Each month you must choose exactly one action.

Available actions:
- hire_dev        : Hire developers. Each costs Rs.2,000 upfront + Rs.5,000/month salary.
- pay_debt        : Spend money to reduce technical debt. Rs.20,000 clears 100% of debt.
- marketing_push  : Spend money on marketing to grow monthly revenue.

Rules:
- Tech debt above 70% destroys revenue and dev productivity. Treat it as an emergency.
- High burn rate (devs x Rs.5,000 + Rs.1,000) drains cash fast. Don't over-hire.
- Marketing only works well when tech debt is low. High debt cancels marketing gains.
- Random events can occur each month (devs quitting, viral spikes, outages).

Respond ONLY with valid JSON — no extra text, no markdown fences:
{
  "action_type": "hire_dev" | "pay_debt" | "marketing_push",
  "amount": <number, used for pay_debt or marketing_push, else 0>,
  "count": <integer, used for hire_dev, else 1>,
  "reasoning": "<one sentence explaining your decision>"
}"""


def ask_llm(observation: dict, task_level: str) -> dict:
    """Send the current observation to Llama via Groq and get an action back."""
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

Debt advice: {observation['tech_debt_details']['recommendation']}

What action do you take this month?"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=256,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if the model wraps in them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def run_episode(task_level: str, max_steps: int = 15):
    print(f"\n{'='*56}")
    print(f"  Baseline Agent — Task: {task_level.upper()}")
    print(f"{'='*56}")

    # Reset environment
    resp = httpx.post(f"{BASE_URL}/reset", params={"task_level": task_level})
    resp.raise_for_status()
    data = resp.json()
    obs = data["observation"]

    print(f"  Start — Cash: Rs.{obs['cash']:,.0f} | "
          f"Debt: {obs['tech_debt']*100:.0f}% | Devs: {obs['devs']}\n")

    total_reward = 0.0
    done = False
    step = 0

    while not done and step < max_steps:
        step += 1

        # LLM decides action
        action_dict = ask_llm(obs, task_level)
        reasoning = action_dict.pop("reasoning", "")

        print(f"  [Month {step:02d}] Action : {action_dict['action_type']}"
              f"  amount={action_dict.get('amount', 0):,.0f}"
              f"  count={action_dict.get('count', 1)}")
        print(f"           Reason : {reasoning}")

        # Send action to environment
        resp = httpx.post(f"{BASE_URL}/step", json=action_dict)
        resp.raise_for_status()
        result = resp.json()

        obs = result["observation"]
        reward = result["reward"]
        done = result["done"]
        msg = result["info"]["message"]
        total_reward += reward

        event_note = f" | Event: {obs['event_message']}" if obs.get("event_message") else ""
        print(f"           State  : Cash=Rs.{obs['cash']:,.0f} | "
              f"Rev=Rs.{obs['monthly_revenue']:,.0f} | "
              f"Debt={obs['tech_debt']*100:.0f}%{event_note}")
        print(f"           Grader : {msg}  (reward={reward:+.3f})\n")

    print(f"  Episode complete. Total reward: {total_reward:.3f}")
    return total_reward


def main():
    scores = {}
    for level in ["easy", "medium", "hard"]:
        scores[level] = run_episode(level)

    print(f"\n{'='*56}")
    print("  Baseline Summary")
    print(f"{'='*56}")
    for level, score in scores.items():
        print(f"  {level.capitalize():8s}: {score:.3f}")
    avg = sum(scores.values()) / len(scores)
    print(f"  {'Average':8s}: {avg:.3f}")
    print(f"{'='*56}\n")


if __name__ == "__main__":
    main()
