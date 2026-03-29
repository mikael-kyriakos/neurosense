import time
from interpreter import interpret

# Simulated input (later replace with your friend's data)
sample_data = {
    "eeg": {"alpha": 0.2, "beta": 0.7, "theta": 0.1, "gamma": 0.3},
    "metrics": {"focus": 35, "stress": 80, "fatigue": 60},
    "context": "User is sitting in a classroom, looking at notes"
}

while True:
    result = interpret(sample_data)
    
    print("\n--- LIVE UPDATE ---")
    print(result)
    
    time.sleep(1)