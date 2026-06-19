import os
import json
import anthropic

CLIENT = None


def _client() -> anthropic.Anthropic:
    global CLIENT
    if CLIENT is None:
        CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return CLIENT


SYSTEM_PROMPT = (
    "You are an expert Hollywood screenwriter and YouTube filmmaker. "
    "Generate compelling, production-ready content for YouTube films. "
    "Structure scripts with clear scene headings (INT./EXT.), action lines, and dialogue. "
    "Keep scenes visual and suitable for AI video generation."
)


def generate_script(prompt: str, title: str) -> str:
    full_text = []
    with _client().messages.stream(
        model="claude-fable-5",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write a complete YouTube film script titled '{title}'.\n\n"
                    f"Premise: {prompt}\n\n"
                    "Include:\n"
                    "1. LOGLINE (one sentence)\n"
                    "2. SYNOPSIS (2-3 paragraphs)\n"
                    "3. FULL SCRIPT (proper screenplay format with INT./EXT. scene headings)"
                ),
            }
        ],
    ) as stream:
        for text in stream.text_stream:
            full_text.append(text)
    return "".join(full_text)


def generate_scene_breakdown(script_text: str) -> list[dict]:
    """Ask Claude to break the script into scenes and return clean JSON."""
    result = _client().messages.create(
        model="claude-fable-5",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": (
                    "Read this film script and return ONLY a JSON array of scenes. "
                    "No explanation, no markdown, just the raw JSON array.\n\n"
                    "Each scene object must have exactly these keys:\n"
                    '  "scene_number": integer\n'
                    '  "location": string\n'
                    '  "description": string (what is visually happening, 2-3 sentences)\n'
                    '  "duration_seconds": integer (5 to 30)\n\n'
                    "Aim for 5-10 scenes total. Start your response with [ and end with ].\n\n"
                    f"SCRIPT:\n{script_text[:6000]}"
                ),
            }
        ],
    )
    raw = result.content[0].text.strip()
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1 or end == 0:
        # Fallback: one scene from the whole script
        return [{"scene_number": 1, "location": "Various", "description": script_text[:300], "duration_seconds": 10}]
    try:
        scenes = json.loads(raw[start:end])
        return scenes if isinstance(scenes, list) and scenes else [
            {"scene_number": 1, "location": "Various", "description": script_text[:300], "duration_seconds": 10}
        ]
    except json.JSONDecodeError:
        return [{"scene_number": 1, "location": "Various", "description": script_text[:300], "duration_seconds": 10}]


def generate_scene_visuals(scene_description: str) -> str:
    """Turn a scene description into a Runway-ready video generation prompt."""
    result = _client().messages.create(
        model="claude-fable-5",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    "Write a cinematic AI video generation prompt for this scene. "
                    "Describe: camera angle, lighting, mood, colors, movement. "
                    "Be specific. Under 150 words. No scene headings, just the visual description.\n\n"
                    f"Scene: {scene_description}"
                ),
            }
        ],
    )
    return result.content[0].text.strip()


def generate_voiceover(script_text: str) -> str:
    """Extract clean narration lines suitable for text-to-speech."""
    result = _client().messages.create(
        model="claude-fable-5",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract the narration and voiceover text from this script as clean spoken sentences. "
                    "Mark pauses with '...' and new scenes with [SCENE N]. "
                    "No stage directions or character names.\n\n"
                    f"{script_text}"
                ),
            }
        ],
    )
    return result.content[0].text.strip()


def generate_title_and_description(script_text: str, title: str) -> dict:
    """Generate YouTube-optimized title, description, and tags."""
    result = _client().messages.create(
        model="claude-fable-5",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Based on this film script titled '{title}', output ONLY a JSON object with:\n"
                    '  "title": SEO YouTube title under 70 characters\n'
                    '  "description": YouTube description 300-500 words\n'
                    '  "tags": array of 15 YouTube tags\n\n'
                    "Start with {{ and end with }}. No other text.\n\n"
                    f"Script:\n{script_text[:3000]}"
                ),
            }
        ],
    )
    text = result.content[0].text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {"title": title, "description": "", "tags": []}
