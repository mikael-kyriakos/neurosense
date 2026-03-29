from interpreter import interpret
from advisor_llm import generate_advice
from camera import CVModule
import time


cv = CVModule(show_window=False)  # show camera window # it showed be False 
cv.start()

last_situation = None 

        # Simulated FULL data
classroomdata = {
    "eeg": {"alpha": 0.2, "beta": 0.7, "theta": 0.1, "gamma": 0.3},
    "metrics": {"focus": 35, "stress": 80, "fatigue": 60},
    "context": "User is sitting in a classroom, looking at notes",
    "physio": {
        "heart_rate": 95,
        "stress_level": 80,
        "sleep_quality": 40
    },

    "behaviour": {
        "steps": 2000,
        "exercise_minutes": 10,
        "food_quality": "poor"
    },

    "journal": "I have exams coming up and feel overwhelmed"
    }

soloworkdata = {
    "eeg": {"alpha": 0.35, "beta": 0.55, "theta": 0.15, "gamma": 0.25},
    "metrics": {"focus": 65, "stress": 40, "fatigue": 30},
    "context": "User is working alone on a laptop, focused on a task",

    "physio": {
        "heart_rate": 78,
        "stress_level": 35,
        "sleep_quality": 70
    },

    "behaviour": {
        "steps": 1200,
        "exercise_minutes": 5,
        "food_quality": "average"
    },

    "journal": "Working alone today. Feeling productive but slightly distracted at times."
}

teamworkdata = {
    "eeg": {"alpha": 0.15, "beta": 0.75, "theta": 0.20, "gamma": 0.40},
    "metrics": {"focus": 55, "stress": 65, "fatigue": 45},
    "context": "User is in a group discussion, collaborating with teammates",

    "physio": {
        "heart_rate": 92,
        "stress_level": 70,
        "sleep_quality": 55
    },

    "behaviour": {
        "steps": 3000,
        "exercise_minutes": 20,
        "food_quality": "good"
    },

    "journal": "Team meeting today. Lots of pressure to contribute. Feeling stressed but engaged."
}

#---Situation based data mapping 
def get_data_for_situation(situation: str) -> dict | None : 
    """
    Returns the appropriate simulated dataset based on the detected situation.
    Returns None if situation is UNKNOWN (no reliable data yet).
    """
    if situation == "SOLO WORK":
        return soloworkdata
 
    elif situation == "STUDY GROUP":
        # Small group study — use classroom data as closest match
        return teamworkdata
 
    elif situation == "MEETING":
        # Active discussion with others — use teamwork data
        return teamworkdata
 
    elif situation == "LECTURE":
        # Passive high-load environment — use classroom data
        return classroomdata
 
    elif situation == "UNKNOWN":
        # CLIP still loading or no people detected — skip this cycle
        return None


try:
    while True:
        state = cv.get_state()
        situation = state.situation 

        if situation == last_situation : 
            time.sleep(1) 
            continue 
        last_situation = situation

        print(state.as_dict())

        data = get_data_for_situation(situation)

        if data is None : 
            print(f"[main] Situation is {situation} - waiting for valid detection.\n")
            time.sleep(1)
            continue
        
# -- Inject data into dat so interpreter knows real environment 
        data["context"] = (
            f"User is in a {state.scene} environment. "
            f"Situation : {situation}. "
            f"People visible : {state.person_count}. "
            f"Session duration :  {state.session_seconds:.0f} seconds. "
            f"Cognitive load : {state.cognitive_load}"
        )

    # Step 1: interpret
        result = interpret(data)

    # Step 2: prepare LLM input
        llm_input = {
        "state": result["state"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"],
        "history": ["Low Attention", "High Stress", "Fatigue"],
        "journal": data["journal"],
        "physio": data["physio"],
        "behaviour": data["behaviour"]
        }

    # Step 3: AI advice
        advice = generate_advice(llm_input)

    # Output
        print("\n--- FINAL OUTPUT ---\n")
        print("STATE:", result["state"])
        print("CONFIDENCE:", result["confidence"])
        print("\nAI ADVICE:\n")
        print(advice)

        time.sleep(1) 

except KeyboardInterrupt:
    print("Stopping...")

finally:
    cv.stop()

