import os
from dotenv import load_dotenv
from huggingface_hub import login, HfApi

# Load environment variables
load_dotenv()

token = os.environ.get('HF_TOKEN')
print(f"Loaded token: {token[:5]}..." if token else "No token found")

try:
    login(token=token)
    print("Login successful!")
    
    # Check if we can access the gated model
    api = HfApi()
    model_id = "Prior-Labs/tabpfn_2_5"
    try:
        model_info = api.model_info(model_id)
        print(f"Successfully accessed {model_id}")
    except Exception as e:
        print(f"Failed to access {model_id}: {e}")
        print("You likely need to accept the terms at: https://huggingface.co/Prior-Labs/tabpfn_2_5")
        
except Exception as e:
    print(f"Login failed: {e}")
