import os

import requests


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")


def _fallback_response(data, is_question):
    state = data.get("state", "Balanced State")
    reasoning = data.get("reasoning") or []
    journal = data.get("journal", "").strip()
    physio = data.get("physio", {}) or {}

    if is_question:
        if "Stress" in state:
            return "You seem to be under pressure right now, so try shrinking the next step and taking a short reset before pushing on."
        if "Fatigue" in state:
            return "You may get more out of a brief break, water, and a lower-effort task before returning to deep work."
        if "Focused" in state or "Engagement" in state:
            return "You look fairly settled, so protect that momentum and avoid switching contexts for a little while."
        return "You look relatively stable right now, so keep the environment calm and check back in after your next task block."

    if journal:
        summary = "Your journal entry suggests a specific lived experience that should be taken at face value rather than generalized."
        cause = "The fallback mode cannot deeply analyze language, so it is safest to stay close to what you actually wrote."
        action = "Reflect on the strongest emotion or difficulty named in the entry and choose one small action that directly addresses it."
        lifestyle = "Use the journal together with rest, movement, nutrition, and workload patterns to see what tends to shift your state."
        pattern = "Treat the journal as first-person evidence; avoid reading extra meaning into it unless the text clearly supports that."
        return (
            f"State Explanation: {summary}\n\n"
            f"Likely Cause: {cause}\n\n"
            f"Action Plan: {action}\n\n"
            f"Lifestyle Suggestions: {lifestyle}\n\n"
            f"Pattern Insight: {pattern}"
        )

    summary = "The signals are relatively balanced." if not reasoning else f"The current picture is being driven by {', '.join(reasoning[:3])}."
    cause = "The model could not reach the external advice service, so this is a local fallback summary."
    action = "Take one manageable next step, reduce obvious distractions, and reassess after a short interval."
    lifestyle = "Hydration, movement, and sleep quality are likely to change this pattern more than pushing harder."
    if "bmi" in physio and "bmi_band" in physio:
        lifestyle += f" Your recorded BMI is {physio['bmi']} ({physio['bmi_band']}), which can be used only as light context rather than a diagnosis."
    pattern = "Use the trends and journal tabs to build a fuller read across multiple snapshots."
    return (
        f"State Explanation: {summary}\n\n"
        f"Likely Cause: {cause}\n\n"
        f"Action Plan: {action}\n\n"
        f"Lifestyle Suggestions: {lifestyle}\n\n"
        f"Pattern Insight: {pattern}"
    )


def generate_advice(data):
    user_input = data.get("journal", "").strip()
    is_question = user_input != "" and ("?" in user_input or len(user_input.split()) <= 12)
    is_journal_analysis = bool(user_input) and not is_question
    excluded_inputs = data.get("excluded_inputs", [])
    exclusion_line = (
        f"Inputs marked unavailable and excluded from reasoning: {excluded_inputs}\n"
        if excluded_inputs
        else ""
    )

    if is_question:
        prompt = f"""
You are a cognitive wellbeing assistant.

Current state: {data['state']}
System confidence score: {data['confidence']}
Signals: {data['reasoning']}
History: {data['history']}
Physio: {data.get('physio')}
Behaviour: {data.get('behaviour')}
{exclusion_line}

User question:
{user_input}

IMPORTANT:
- Answer in SECOND PERSON
- Be conversational and natural
- Keep it short (2-4 sentences)
- No bullet points
- No headings
- No structured formatting
- "System confidence score" means the model's confidence in the classification, not the user's personal confidence or self-esteem.
- Do not use or speculate about any input listed as unavailable or excluded.
- If height, weight, or BMI are provided, you must determine whether the BMI is inside or outside the healthy range.
- Treat BMI 18.5 to 24.9 as healthy range; below 18.5 or above 24.9 is outside the healthy range.
- If BMI is outside the healthy range, you must mention that in the answer in a gentle, non-alarmist way.
- Do not treat BMI as a diagnosis or make extreme medical claims from it.

Answer the question directly.
"""
    else:
        journal_instructions = ""
        if is_journal_analysis:
            journal_instructions = f"""
Journal text to analyze:
{user_input}

JOURNAL ANALYSIS RULES:
- Base your analysis primarily and explicitly on the journal text above.
- Treat the journal text as the main evidence source when it is present.
- Do not generalize away from the journal into generic wellbeing advice unless it clearly connects back to the journal text.
- If you mention emotions, pressures, motivations, or struggles, they must be supported by what the user actually wrote.
- If the journal is ambiguous, say it is ambiguous instead of inventing detail.
- Do not interpret "confidence" as the user's self-confidence. In this app, confidence means the system's confidence in the model output.
- In "Pattern Insight", refer to the wording or themes in the journal entry when possible.
"""

        prompt = f"""
You are a cognitive wellbeing assistant.

Current state: {data['state']}
System confidence score: {data['confidence']}
Signals: {data['reasoning']}
History: {data['history']}
Physio: {data.get('physio')}
Behaviour: {data.get('behaviour')}
{exclusion_line}
{journal_instructions}

Provide a structured analysis using these exact headings:

State Explanation:
Likely Cause:
Action Plan:
Lifestyle Suggestions:
Pattern Insight:

IMPORTANT:
- Speak in SECOND PERSON
- Be clear and helpful
- Keep it readable and not overly long
- The system confidence score is the model's confidence in the classification, not the user's self-confidence.
- If journal text is present, anchor each section to the journal text first and use the other signals only as secondary context.
- Do not mention, infer from, or give advice about any input listed as unavailable or excluded.
- If height, weight, BMI, or BMI band are present, you must determine whether the BMI is inside or outside the healthy range.
- Treat BMI 18.5 to 24.9 as healthy range; below 18.5 or above 24.9 is outside the healthy range.
- If BMI is outside the healthy range, you must explicitly bring that up in the guidance in a gentle, non-alarmist way.
- You must not present BMI as a diagnosis.
- Do not over-weight BMI in the analysis; keep it secondary to the user's current signals, behaviour, and journal text.
"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
            timeout=18,
        )
        response.raise_for_status()
        result = response.json()
        if "choices" not in result:
            return _fallback_response(data, is_question)
        return result["choices"][0]["message"]["content"]
    except Exception:
        return _fallback_response(data, is_question)
