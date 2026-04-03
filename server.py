from fastapi import FastAPI, HTTPException
from models import Action
from core import SaaSState
from tasks import EasyTask, MediumTask, HardTask

app = FastAPI(title="SaaS-Ops OpenEnv", version="1.0")

env_state = None
current_task = None

@app.post("/reset")
def reset(task_level: str = "medium"):
    global env_state, current_task
    
    level = task_level.lower()
    
    if level == "easy":
        # Start with high debt and limited budget as per prompt
        env_state = SaaSState(init_cash=20000.0, init_devs=2, init_debt=0.8, init_revenue=0.0)
        current_task = EasyTask()
    elif level == "medium":
        # Start from zero revenue
        env_state = SaaSState(init_cash=50000.0, init_devs=1, init_debt=0.1, init_revenue=0.0)
        current_task = MediumTask()
    elif level == "hard":
        # Long term pivot
        env_state = SaaSState(init_cash=30000.0, init_devs=3, init_debt=0.4, init_revenue=2000.0)
        current_task = HardTask()
    else:
        raise HTTPException(status_code=400, detail="Invalid task level (use easy, medium or hard)")
        
    return {
        "observation": env_state.get_observation().model_dump(),
        "info": {"task": level, "status": "Environment reset"}
    }

@app.post("/step")
def step(action: Action):
    global env_state, current_task
    
    if not env_state:
        raise HTTPException(status_code=400, detail="Environment has not been initialized. Call /reset first.")
        
    obs, env_done, env_reward = env_state.step(action)
    
    # Member 3 Focus: Task evaluation
    task_reward, task_done, msg = current_task.evaluate(env_state, env_done)
    
    final_reward = env_reward + task_reward
    final_done = env_done or task_done
    
    return {
        "observation": obs.model_dump(),
        "reward": final_reward,
        "done": final_done,
        "info": {
            "message": msg,
            "month": env_state.current_month
        }
    }

@app.get("/state")
def get_state():
    if not env_state:
        raise HTTPException(status_code=400, detail="Environment not initialized.")
    return env_state.get_observation().model_dump()
