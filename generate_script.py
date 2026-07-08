"""
generate_script.py
Channel: Nobody Tells You
Generates faceless documentary-style scripts using the proven 6-filter formula
distilled from three successful channels. Core principle: OPEN THE CURIOSITY GAP
EARLY, KEEP IT OPEN, AND SAVE THE REAL PAYOFF FOR THE VERY END (retention-first).

Requires: GROQ_API_KEY in environment (or NTY_GROQ_API_KEY).
Usage:    python generate_script.py "Why you're always tired"
Output:   writes script.txt and meta.txt in the working directory.
"""

import os
import sys
import json
import re
import urllib.request

# ---- Config -----------------------------------------------------------------
GROQ_API_KEY = os.environ.get("NTY_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("NTY_GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Target length. ~130 wpm narration => 1600 words ~= 12 min.
TARGET_WORDS = int(os.environ.get("NTY_TARGET_WORDS", "1900"))

CHANNEL_NAME = "Nobody Tells You"

# ---- The formula (system prompt) -------------------------------------------
# This is the heart of the automation. It encodes the 6-filter structure and,
# above all, the retention rule: the biggest revelation is withheld until the end.
SYSTEM_PROMPT = f"""
You are the head writer for a faceless YouTube channel called "{CHANNEL_NAME}".
The channel exposes the invisible systems, incentives, and quiet truths that
run people's lives but that nobody explains to them. Topics span money, time,
work, media, habits, status, health, cities, debt, attention — anything where
there is a comfortable lie on the surface and a hidden machine underneath.

Your single most important job is RETENTION. You keep the viewer watching to the
final second by opening a curiosity gap immediately and refusing to fully close
it until the very end. You tease the real answer, circle it, deepen the mystery,
hand out small rewards along the way — but the biggest "aha" is SAVED FOR THE
FINAL SECTION. Never give away the core payoff in the first half.

Write ONE continuous narration script in ENGLISH, meant to be read aloud by a
single calm, authoritative, intelligent narrator (text-to-speech). Do NOT include
any headers, labels, stage directions, timestamps, speaker names, scene notes,
or bracketed cues. Output ONLY the spoken words, in flowing paragraphs. No lists.

Follow this 6-part internal structure WITHOUT ever labeling it:

1. HOOK (open the loop). Start with a vivid, specific, slightly unsettling scene
   or a sharp question. Within the first few sentences, plant the central
   question the whole video will answer — but DO NOT answer it. Make the viewer
   need to know. End the opening beat by promising, implicitly, that the truth is
   coming, and invite a like naturally if it fits.

2. THE LIE. Name the comfortable belief the viewer already holds about this topic
   ("you were told X"). Then crack it. Show that the thing everyone accepts is not
   what it seems. Create unease and disbelief.

3. EVIDENCE & AUTHORITY. Bring concrete, specific proof: real numbers, dates,
   named experts, historical examples, mechanisms. Build trust and make it feel
   rigorous. But keep FEEDING the mystery — every fact should raise the stakes,
   not resolve them.

4. DIRECT "YOU". Turn to the viewer. Use "you" and "your". Put them inside the
   story. Make them feel this system is operating on THEM, right now. This is
   where it stops being trivia and becomes personal.

5. RAISE THE TENSION. Escalate with lines like "but here's the part that breaks
   people's brains" or "and this is where it gets genuinely strange". Deepen the
   open loop. Reveal a further layer that makes the earlier facts more disturbing.
   Still DO NOT deliver the final payoff. If there is a soft call-to-action or a
   single sponsor-style aside, it can live here, mid-video, without killing the
   momentum.

6. THE PAYOFF (curiosity, saved for last). NOW deliver the real revelation you've
   been withholding — the answer to the question from the hook. Make it land as a
   twist or a reframe that recontextualizes everything before it. Then close on a
   resonant, slightly philosophical note that makes the viewer want to share it,
   and end with a natural subscribe prompt.

TONE: calm, confident, "a smart friend telling you the truth nobody else will."
Short, punchy sentences mixed with longer ones. Frequent tiny payoffs to keep
attention, but the MAIN payoff is always last. Second person. No fluff, no empty
sentences — every line adds information, tension, or emotion. Be accurate; if you
use a statistic or claim, keep it realistic and defensible. Avoid clichés and
avoid sounding like an ad. Never break character or mention that you are an AI.

LENGTH: approximately {TARGET_WORDS} words.
"""

USER_TEMPLATE = """Topic for this episode: {topic}

Write the full narration script now, following the structure and the retention
rule (biggest revelation last). Output ONLY the spoken narration."""

# Separate, cheaper call for the meta (title/description/tags).
META_SYSTEM = f"""
You write YouTube metadata for the faceless channel "{CHANNEL_NAME}", which exposes
hidden systems and truths. Given a topic and its script, produce metadata that
maximizes click-through while staying honest and matching the channel voice.

Return STRICT JSON ONLY (no markdown, no backticks) with exactly these keys:
"title": a curiosity-gap title, ideally starting with or containing the channel's
         hook style (e.g. "Nobody Tells You ..." or a bold claim). Under 90 chars.
"description": 2 short paragraphs that tease the video without spoiling the ending,
               followed by a line inviting subscription.
"chapters": an array of 6 to 8 objects, each {{"time": "M:SS", "label": "..."}},
            approximate timestamps for a ~{TARGET_WORDS//150}-minute video, where the
            final chapter hints at the payoff WITHOUT revealing it.
"tags": an array of 12-18 lowercase search tags relevant to the topic and niche.
"""

META_USER = """Topic: {topic}

Script:
{script}

Return the JSON now."""


def _post(payload):
    if not GROQ_API_KEY:
        sys.exit("ERROR: set NTY_GROQ_API_KEY (or GROQ_API_KEY) in the environment.")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROQ_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def generate_script(topic):
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.8,
        "max_tokens": 6000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(topic=topic)},
        ],
    }
    out = _post(payload)
    text = out["choices"][0]["message"]["content"].strip()
    # Safety: strip any accidental leading label lines.
    text = re.sub(r"^\s*(script|narration)\s*[:\-]\s*", "", text, flags=re.I)
    return text


def generate_meta(topic, script):
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.6,
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": META_SYSTEM},
            {"role": "user", "content": META_USER.format(topic=topic, script=script[:6000])},
        ],
    }
    out = _post(payload)
    raw = out["choices"][0]["message"]["content"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        meta = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback minimal meta if the model returns something off.
        meta = {
            "title": f"Nobody Tells You: {topic}",
            "description": f"The hidden truth about {topic}.\n\nSubscribe for more.",
            "chapters": [],
            "tags": [topic.lower(), "nobody tells you", "hidden systems", "documentary"],
        }
    return meta


def meta_to_text(meta):
    """Render meta dict into the meta.txt format: title first line, then body."""
    lines = [meta.get("title", "").strip(), ""]
    desc = meta.get("description", "").strip()
    if desc:
        lines.append(desc)
        lines.append("")
    chapters = meta.get("chapters") or []
    if chapters:
        lines.append("Chapters:")
        for c in chapters:
            t = str(c.get("time", "")).strip()
            lab = str(c.get("label", "")).strip()
            if t and lab:
                lines.append(f"{t} {lab}")
        lines.append("")
    tags = meta.get("tags") or []
    if tags:
        lines.append("Subscribe for more of what nobody tells you.")
        lines.append("")
        lines.append(" ".join(f"#{re.sub(r'[^a-z0-9]', '', t.lower())}" for t in tags if t))
    return "\n".join(lines).strip() + "\n"


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python generate_script.py "Topic here"')
    topic = sys.argv[1].strip()

    print(f"[generate_script] Topic: {topic}")
    script = generate_script(topic)
    wc = len(script.split())
    print(f"[generate_script] Script generated: {wc} words")

    meta = generate_meta(topic, script)
    meta_text = meta_to_text(meta)

    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(script.strip() + "\n")
    with open("meta.txt", "w", encoding="utf-8") as f:
        f.write(meta_text)

    print("[generate_script] Wrote script.txt and meta.txt")


if __name__ == "__main__":
    main()
