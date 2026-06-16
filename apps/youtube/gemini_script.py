"""Gemini script generator via Vertex AI — drop-in for script_generator.py."""
import json
import os
from google import genai
from google.oauth2 import service_account

PRO = "gemini-2.5-pro"

SYSTEM = """You are an expert Hollywood screenwriter and YouTube filmmaker for Dominion Healing.
Tone: bold, faith-driven, empowering. Generate compelling, production-ready content.
Structure all scripts with clear scene headings, action lines, and dialogue.
Keep scenes visual and suitable for AI video generation."""


def _client():
    project  = os.environ.get("GCP_PROJECT_ID", "")
    location = os.environ.get("GCP_REGION", "us-central1")
    sa_json  = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        project = project or info.get("project_id", "")
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return genai.Client(vertexai=True, project=project, location=location, credentials=creds)
    return genai.Client(vertexai=True, project=project, location=location)


def generate_script(prompt: str, title: str) -> str:
    c = _client()
    msg = (
        f"Write a complete YouTube film script titled '{title}'.\n\n"
        f"Premise: {prompt}\n\n"
        "Format:\n"
        "1. LOGLINE (one sentence)\n"
        "2. SYNOPSIS (2-3 paragraphs)\n"
        "3. FULL SCRIPT (proper screenplay format)\n"
        "4. SCENE BREAKDOWN (JSON list: scene_number, location, time_of_day, "
        "description, dialogue_summary, duration_seconds)"
    )
    r = c.models.generate_content(model=PRO, contents=SYSTEM + "\n\n" + msg)
    return r.text


def generate_scene_visuals(scene_description: str) -> str:
    c = _client()
    r = c.models.generate_content(
        model=PRO,
        contents=(
            "Convert this scene description into a detailed visual generation prompt "
            "for an AI video tool. Be specific about lighting, camera angle, mood, and "
            "visual style. Keep it under 200 words.\n\nScene: " + scene_description
        ),
    )
    return r.text


def generate_voiceover(script_text: str) -> str:
    c = _client()
    r = c.models.generate_content(
        model=PRO,
        contents=(
            "Extract and rewrite only the narration and voiceover text from this script "
            "as clean, spoken sentences suitable for text-to-speech. "
            "Include natural pauses marked with '...' and scene markers like [SCENE 1].\n\n"
            + script_text
        ),
    )
    return r.text


def generate_title_and_description(script_text: str, title: str) -> dict:
    c = _client()
    r = c.models.generate_content(
        model=PRO,
        contents=(
            f"Based on this film script titled '{title}', generate:\n"
            "1. An SEO-optimized YouTube title (max 70 chars)\n"
            "2. A YouTube description (300-500 words, include timestamps placeholder)\n"
            "3. 15 relevant YouTube tags\n\n"
            'Respond in JSON: {"title": "...", "description": "...", "tags": [...]}\n\n'
            f"Script excerpt:\n{script_text[:3000]}"
        ),
    )
    text = r.text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {"title": title, "description": "", "tags": []}
