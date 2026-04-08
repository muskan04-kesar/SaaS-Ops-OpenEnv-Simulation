from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from groq import Groq
from openai import OpenAI
from models import Action
from core import SaaSState
from tasks import EasyTask, MediumTask, HardTask

app = FastAPI(title="SaaS-Ops OpenEnv", version="1.0")

# Hugging Face deployment often requires CORS for local agents to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI Setup
GROQ_KEY = os.getenv("GROQ_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")

# Priority: HF_TOKEN (OpenAI Client) > GROQ_KEY (Groq Client)
if HF_TOKEN:
    ai_client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)
elif GROQ_KEY:
    ai_client = Groq(api_key=GROQ_KEY)
else:
    ai_client = None

env_state = None
current_task = None

def enrich_observation_with_ai(obs):
    """
    If an AI client is found, we replace the hardcoded advice 
    with real AI-generated strategy recommendations.
    """
    if not ai_client:
        return obs

    try:
        # Construct a prompt for the 'AI COO'
        prompt = f"""
        You are a SaaS COO Advisor. Analyze this state and provide 1-sentence advice.
        State: Cash Rs.{obs.cash:,.0f}, MRR Rs.{obs.monthly_revenue:,.0f}, Tech Debt {obs.tech_debt*100:.0f}%, Devs {obs.devs}.
        
        Output JSON:
        {{
            "reasoning": "Why are we in this state?",
            "impact_on_revenue": "How is debt affecting us?",
            "recommendation": "What should we do NEXT month?"
        }}
        """
        
        chat_completion = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_NAME,
            response_format={"type": "json_object"} if "llama-3" in MODEL_NAME.lower() else None,
            max_tokens=256
        )
        
        ai_advice = json.loads(chat_completion.choices[0].message.content)
        obs.tech_debt_details.reasoning = ai_advice.get("reasoning", obs.tech_debt_details.reasoning)
        obs.tech_debt_details.impact_on_revenue = ai_advice.get("impact_on_revenue", obs.tech_debt_details.impact_on_revenue)
        obs.tech_debt_details.recommendation = ai_advice.get("recommendation", obs.tech_debt_details.recommendation)
    except Exception as e:
        print(f"AI enrichment failed: {e}")
    
    return obs

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.post("/reset")
def reset(task_level: str = "medium"):
    global env_state, current_task
    
    level = task_level.lower()
    
    if level == "easy":
        env_state = SaaSState(init_cash=20000.0, init_devs=2, init_debt=0.8, init_revenue=0.0)
        current_task = EasyTask()
    elif level == "medium":
        env_state = SaaSState(init_cash=50000.0, init_devs=1, init_debt=0.1, init_revenue=0.0)
        current_task = MediumTask()
    elif level == "hard":
        env_state = SaaSState(init_cash=30000.0, init_devs=3, init_debt=0.4, init_revenue=2000.0)
        current_task = HardTask()
    else:
        raise HTTPException(status_code=400, detail="Invalid task level")
        
    obs = env_state.get_observation()
    obs = enrich_observation_with_ai(obs)
    
    return {
        "observation": obs.model_dump(),
        "info": {"task": level, "status": "Environment reset"}
    }

@app.post("/step")
def step(action: Action):
    global env_state, current_task
    
    if not env_state:
        raise HTTPException(status_code=400, detail="Environment not initialized.")
        
    obs, env_done, env_reward = env_state.step(action)
    obs = enrich_observation_with_ai(obs)
    
    task_reward, task_done, msg = current_task.evaluate(env_state, env_done)
    
    return {
        "observation": obs.model_dump(),
        "reward": env_reward + task_reward,
        "done": env_done or task_done,
        "info": {"message": msg, "month": env_state.current_month}
    }

@app.get("/state")
def get_state():
    if not env_state:
        raise HTTPException(status_code=400, detail="Environment not initialized.")
    return enrich_observation_with_ai(env_state.get_observation()).model_dump()

def main():
    import uvicorn
    # Updated to point to the new location server.app
    uvicorn.run("server.app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)

if __name__ == "__main__":
    main()
