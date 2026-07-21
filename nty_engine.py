import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DEFAULT_TOPIC = "The $9,000 Decision Nobody Warns You About"
MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
API_URL = "https://api.groq.com/openai/v1/chat/completions"


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return value.strip("-") or "video"


def groq(prompt: str, attempts: int = 5) -> str:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise SystemExit("GROQ_API_KEY secret is missing.")
    for attempt in range(1, attempts + 1):
        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "temperature": 0.85,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "Follow the instructions exactly and return valid JSON only, matching the requested schema.",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=180,
        )
        if response.ok:
            break
        if response.status_code in (429, 503) and attempt < attempts:
            print(f"Groq {response.status_code}, retrying ({attempt}/{attempts})...", flush=True)
            time.sleep(20 * attempt)
            continue
        raise SystemExit(
            f"Groq request failed: HTTP {response.status_code}: {response.text[:800]}"
        )
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"Unexpected Groq response: {json.dumps(data)[:1000]}") from exc


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Groq returned invalid JSON: {text[:1200]}") from exc


def build_prompt(topic: str) -> str:
    return f"""
You are the scriptwriter for the English YouTube channel "Nobody Tells You" — a serious,
authoritative voice that exposes the uncomfortable truths about money, life, and human
behavior that most people never hear out loud.

Write one video package about: {topic}

Return valid JSON only with this exact top-level structure:
{{
  "meta": {{
    "title": "under 100 characters, curiosity-gap, no clickbait punctuation spam",
    "description": "2 to 3 sentence YouTube description",
    "hashtags": ["#example", "#example2"]
  }},
  "beats": [
    "one short sentence, 3 to 4 seconds spoken, a single micro-scene",
    "another short sentence beat"
  ]
}}

Rules:
- English only, serious and authoritative tone, second person or narrative third person.
- 90 to 140 beats. Each beat is ONE short sentence or sentence fragment, never more than
  one idea per beat, matching a fast visual cut every 3 to 4 seconds.
- Open with a concrete, specific hook (a number, a scene, a decision), never a generic
  question.
- Build the case slowly. Reveal costs, mechanisms, and consequences nobody usually adds up.
- Do NOT resolve the central tension early. Hold back the biggest insight, twist, or payoff
  for the final 10 to 15 beats.
- End with the single most surprising or costly truth, then a one-line call to subscribe.
- Never closely paraphrase a specific real video. Invent an original angle, original
  examples, and original numbers or scenarios that illustrate the idea honestly.
- No brackets, no scene directions, no narrator labels, just the spoken lines.
"""


def validate(package: dict) -> None:
    required = {"meta", "beats"}
    missing = required - package.keys()
    if missing:
        raise SystemExit(f"Missing package sections: {sorted(missing)}")
    beats = package["beats"]
    if not isinstance(beats, list) or len(beats) < 20:
        raise SystemExit("Groq returned too few beats.")
    meta = package["meta"]
    if not str(meta.get("title", "")).strip():
        raise SystemExit("Missing meta field: title")


def write_outputs(package: dict, topic: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    project_dir = Path("projects") / f"{timestamp}-{slugify(topic)}"
    project_dir.mkdir(parents=True, exist_ok=True)

    beats = [str(beat).strip() for beat in package["beats"] if str(beat).strip()]
    script = "\n\n".join(beats)

    meta = package["meta"]
    meta_txt = "\n".join([
        str(meta["title"]).strip(),
        "",
        str(meta.get("description", "")).strip(),
        "",
        " ".join(meta.get("hashtags", [])),
    ]).strip()

    files = {
        "script.txt": script,
        "meta.txt": meta_txt,
        "package.json": json.dumps(package, ensure_ascii=False, indent=2),
    }
    for name, content in files.items():
        Path(name).write_text(content, encoding="utf-8")
        (project_dir / name).write_text(content, encoding="utf-8")
    return project_dir


def main() -> None:
    topic = os.environ.get("VIDEO_TOPIC") or (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC)
    topic = topic.strip() or DEFAULT_TOPIC
    package = parse_json(groq(build_prompt(topic)))
    validate(package)
    project_dir = write_outputs(package, topic)
    print(f"Nobody-Tells-You engine complete: {project_dir}")
    print(f"Title: {package['meta']['title']}")


if __name__ == "__main__":
    main()
