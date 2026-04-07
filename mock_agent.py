from server.app import reset, step
from models import Action
import random

# Integration Lead (Member 3): Setup Mock Agent against Task Graders

def run_mock_agent(task_level):
    print(f"\n================================================")
    print(f"=== Starting Mock Agent on {task_level.upper()} Task ===")
    print(f"================================================\n")
    
    # Reset Environment
    res = reset(task_level=task_level)
    state = res["observation"]
    
    print(f"Initial State -> Cash: {state['cash']}, Debt: {state['tech_debt']:.2f}, Devs: {state['devs']}")
    
    done = False
    step_count = 0
    total_reward = 0.0
    
    # Hard requires 12 months minimum to survive.
    max_steps = 15 
    
    while not done and step_count < max_steps:
        step_count += 1
        
        # Mock random player logic
        action_choice = random.choice(["hire_dev", "pay_debt", "marketing_push"])
        
        if action_choice == "hire_dev":
            action = Action(action_type=action_choice, count=1)
        elif action_choice == "pay_debt":
            action = Action(action_type=action_choice, amount=random.uniform(2000, 8000))
        else:
            action = Action(action_type=action_choice, amount=random.uniform(3000, 10000))
            
        print(f"\n[Month {step_count}] Agent executing: {action}")
        
        data = step(action=action)
        
        obs = data["observation"]
        reward = data["reward"]
        done = data["done"]
        info = data["info"]
        
        total_reward += reward
        
        print(f"  --> Observation: Cash={obs['cash']:.2f}, Rev={obs['monthly_revenue']:.2f}, Debt={obs['tech_debt']:.2f}, Devs={obs['devs']}, Features={obs['features_completed']}")
        print(f"  --> Grader Message: {info['message'].replace('≤', '<=')}")
        print(f"  --> Step Reward: {reward}")
        
    print(f"\n*** Episode Finished for {task_level.title()}. Total Reward: {total_reward:.2f} ***\n")

if __name__ == "__main__":
    for task in ["easy", "medium", "hard"]:
        run_mock_agent(task)
