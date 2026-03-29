def extract_features(data):
    eeg = data["eeg"]
    metrics = data["metrics"]
    context = data["context"].lower()

    physio = data.get("physio", {})
    behaviour = data.get("behaviour", {})
    available_inputs = data.get("available_inputs", {})

    def is_available(section, key):
        return available_inputs.get(section, {}).get(key, True)

    return {
        # Core
        "high_stress": is_available("metrics", "stress") and metrics["stress"] > 70,
        "low_focus": is_available("metrics", "focus") and metrics["focus"] < 40,
        "high_focus": is_available("metrics", "focus") and metrics["focus"] > 70,
        "fatigued": is_available("metrics", "fatigue") and metrics["fatigue"] > 70,

        # Brain waves
        "beta_dominant": eeg["beta"] > max(eeg.values()),
        "theta_dominant": eeg["theta"] > max(eeg.values()),
        "gamma_dominant": eeg["gamma"] > max(eeg.values()),

        # Context
        "in_classroom": "classroom" in context,
        "on_phone": "phone" in context,

        # Physiological
        "high_heart_rate": is_available("physio", "heart_rate") and physio.get("heart_rate", 0) > 90,
        "high_physical_stress": is_available("physio", "stress_level") and physio.get("stress_level", 0) > 70,
        "poor_sleep": is_available("physio", "sleep_quality") and physio.get("sleep_quality", 100) < 50,

        # Behavioural
        "low_activity": is_available("behaviour", "steps") and behaviour.get("steps", 10000) < 3000,
        "low_exercise": is_available("behaviour", "exercise_minutes") and behaviour.get("exercise_minutes", 60) < 20,
        "poor_diet": is_available("behaviour", "food_quality") and behaviour.get("food_quality", "") == "poor",
    }


def predict(features):
    score = 0
    reasoning = []
    agreement = 0  # 🔥 for confidence

    # -------------------------
    # CORE SIGNALS
    # -------------------------
    if features["high_stress"]:
        score += 3
        reasoning.append("high stress detected")
        agreement += 1

    if features["low_focus"]:
        score += 2
        reasoning.append("low attention")
        agreement += 1

    if features["high_focus"]:
        score += 2
        reasoning.append("high focus")
        agreement += 1

    # -------------------------
    # BRAIN WAVES
    # -------------------------
    if features["beta_dominant"]:
        score += 2
        reasoning.append("beta waves indicate stress")
        agreement += 1

    if features["theta_dominant"]:
        reasoning.append("theta waves indicate fatigue")
        agreement += 1

    if features["gamma_dominant"]:
        reasoning.append("gamma waves indicate deep cognition")
        agreement += 1

    # -------------------------
    # PHYSIO
    # -------------------------
    if features["high_physical_stress"]:
        score += 1
        reasoning.append("high physiological stress")
        agreement += 1

    if features["high_heart_rate"]:
        reasoning.append("elevated heart rate")
        agreement += 1

    if features["poor_sleep"]:
        reasoning.append("poor sleep quality")
        agreement += 1

    # -------------------------
    # BEHAVIOUR
    # -------------------------
    if features["low_activity"]:
        reasoning.append("low activity levels")
        agreement += 1

    if features["poor_diet"]:
        reasoning.append("poor diet")
        agreement += 1

    # -------------------------
    # CONTEXT
    # -------------------------
    if features["in_classroom"]:
        reasoning.append("learning environment")

    if features["on_phone"]:
        reasoning.append("phone distraction")

    # -------------------------
    # STATE CLASSIFICATION
    # -------------------------
    if features["high_stress"] and features["in_classroom"]:
        state = "High Stress in Learning Context"

    elif features["on_phone"] and features["low_focus"]:
        state = "Distracted by External Stimuli"

    elif features["theta_dominant"] or features["fatigued"]:
        state = "Cognitive Fatigue"

    elif features["gamma_dominant"] and features["high_focus"]:
        state = "Deep Cognitive Engagement"

    elif features["high_focus"]:
        state = "Focused State"

    else:
        state = "Balanced State"

    # -------------------------
    # 🔥 NEW CONFIDENCE CALCULATION
    # -------------------------

    max_possible = 10  # total meaningful signals
    agreement_ratio = agreement / max_possible

    # stability factor (based on score strength)
    strength = min(score / 10, 1)

    confidence = 0.5 + (agreement_ratio * 0.3) + (strength * 0.2)
    confidence = round(min(confidence, 0.95), 2)

    return state, confidence, reasoning


def generate_advice(state):
    if "Stress" in state:
        return "Take a short break or reduce workload."
    if "Fatigue" in state:
        return "Rest or switch tasks."
    if "Distracted" in state:
        return "Remove distractions."
    if "Focused" in state:
        return "Maintain this state."
    return "Maintain balance."


def interpret(data):
    features = extract_features(data)
    state, confidence, reasoning = predict(features)

    return {
        "state": state,
        "confidence": confidence,
        "reasoning": reasoning,
        "advice": generate_advice(state)
    }
