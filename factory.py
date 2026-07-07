"""
factory.py
Channel: Nobody Tells You
End-to-end faceless video pipeline:
  1. pull next topic from topics.txt
  2. generate script + meta (generate_script.py)
  3. narrate with edge-tts
  4. fetch/generate background images (Pollinations)
  5. assemble video with ffmpeg
  6. upload to YouTube (Data API v3)

Designed to run on GitHub Actions from a mobile-only workflow.
All secrets use the NTY_ prefix so this channel never collides with others.
"""

import os
import sys
import glob
import json
import time
import base64
import subprocess
import urllib.parse
import urllib.request

import generate_script  # local module

# ---- Config -----------------------------------------------------------------
VOICE = os.environ.get("NTY_TTS_VOICE", "en-US-ChristopherNeural")
TTS_RATE = os.environ.get("NTY_TTS_RATE", "-6%")     # slightly slower = documentary
TTS_PITCH = os.environ.get("NTY_TTS_PITCH", "-2Hz")
IMAGE_COUNT = int(os.environ.get("NTY_IMAGE_COUNT", "12"))
IMAGE_STYLE = os.environ.get(
    "NTY_IMAGE_STYLE",
    "dark cinematic documentary still, muted desaturated tones, dramatic lighting, "
    "film grain, moody, no text, no watermark",
)
WIDTH, HEIGHT = 1920, 1080
WORK = os.path.abspath(os.environ.get("NTY_WORKDIR", "build"))
TOPICS_FILE = os.environ.get("NTY_TOPICS_FILE", "topics.txt")


def run(cmd, **kw):
    print("+", " ".join(cmd) if isinstance(cmd, list) else cmd)
    return subprocess.run(cmd, check=True, **kw)


# ---- 1. topic ---------------------------------------------------------------
def next_topic():
    if not os.path.exists(TOPICS_FILE):
        sys.exit(f"ERROR: {TOPICS_FILE} not found.")
    with open(TOPICS_FILE, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    if not lines:
        sys.exit("No topics left in topics.txt.")
    topic = lines[0]
    # pop the used topic, keep the rest
    remaining = lines[1:]
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + ("\n" if remaining else ""))
    return topic


# ---- 2. script --------------------------------------------------------------
def make_script(topic):
    script = generate_script.generate_script(topic)
    meta = generate_script.generate_meta(topic, script)
    meta_text = generate_script.meta_to_text(meta)
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, "script.txt"), "w", encoding="utf-8") as f:
        f.write(script.strip() + "\n")
    with open(os.path.join(WORK, "meta.txt"), "w", encoding="utf-8") as f:
        f.write(meta_text)
    return script, meta


# ---- 3. narration -----------------------------------------------------------
def narrate(script):
    audio = os.path.join(WORK, "narration.mp3")
    script_path = os.path.join(WORK, "script.txt")
    run([
        "edge-tts",
        "--voice", VOICE,
        "--rate", TTS_RATE,
        "--pitch", TTS_PITCH,
        "-f", script_path,
        "--write-media", audio,
    ])
    return audio


def audio_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


# ---- 4. images --------------------------------------------------------------
def fetch_images(topic, n):
    os.makedirs(os.path.join(WORK, "img"), exist_ok=True)
    paths = []
    for i in range(n):
        prompt = f"{topic}, {IMAGE_STYLE}"
        seed = 1000 + i
        url = (
            "https://image.pollinations.ai/prompt/"
            + urllib.parse.quote(prompt)
            + f"?width={WIDTH}&height={HEIGHT}&seed={seed}&nologo=true"
        )
        dst = os.path.join(WORK, "img", f"img_{i:03d}.jpg")
        for attempt in range(3):
            try:
                urllib.request.urlretrieve(url, dst)
                if os.path.getsize(dst) > 5000:
                    paths.append(dst)
                    break
            except Exception as e:
                print(f"  image {i} attempt {attempt+1} failed: {e}")
                time.sleep(3)
    if not paths:
        sys.exit("ERROR: no images fetched.")
    return paths


# ---- 5. video ---------------------------------------------------------------
def build_video(images, audio):
    dur = audio_duration(audio)
    per = max(dur / len(images), 1.0)
    listfile = os.path.join(WORK, "frames.txt")
    with open(listfile, "w") as f:
        for p in images:
            f.write(f"file '{os.path.abspath(p)}'\n")
            f.write(f"duration {per:.3f}\n")
        f.write(f"file '{os.path.abspath(images[-1])}'\n")  # last frame repeat

    silent = os.path.join(WORK, "silent.mp4")
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
               f"crop={WIDTH}:{HEIGHT},format=yuv420p",
        "-r", "30", silent,
    ])

    final = os.path.join(WORK, "video.mp4")
    run([
        "ffmpeg", "-y", "-i", silent, "-i", audio,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-shortest", final,
    ])
    return final


# ---- 6. upload --------------------------------------------------------------
def yt_access_token():
    cid = os.environ["NTY_YT_CLIENT_ID"]
    csec = os.environ["NTY_YT_CLIENT_SECRET"]
    refresh = os.environ["NTY_YT_REFRESH_TOKEN"]
    data = urllib.parse.urlencode({
        "client_id": cid,
        "client_secret": csec,
        "refresh_token": refresh,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["access_token"]


def parse_meta(meta_text):
    lines = meta_text.splitlines()
    title = lines[0].strip() if lines else "Nobody Tells You"
    body = "\n".join(lines[1:]).strip()
    tags = []
    for l in lines:
        if l.strip().startswith("#"):
            tags = [t.lstrip("#") for t in l.split()]
    return title, body, tags


def upload(video, meta_text):
    token = yt_access_token()
    title, description, tags = parse_meta(meta_text)
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags[:30],
            "categoryId": "27",  # Education
        },
        "status": {"privacyStatus": os.environ.get("NTY_PRIVACY", "private"),
                   "selfDeclaredMadeForKids": False},
    }
    # resumable upload, minimal implementation
    init = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(metadata).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/*",
        },
        method="POST",
    )
    with urllib.request.urlopen(init, timeout=60) as r:
        location = r.headers["Location"]

    size = os.path.getsize(video)
    with open(video, "rb") as f:
        put = urllib.request.Request(
            location, data=f.read(),
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "video/*",
                     "Content-Length": str(size)},
            method="PUT",
        )
        with urllib.request.urlopen(put, timeout=1800) as r:
            resp = json.loads(r.read())
    vid = resp.get("id")
    print(f"[upload] Uploaded: https://youtu.be/{vid}")
    return vid


# ---- main -------------------------------------------------------------------
def main():
    topic = next_topic()
    print(f"=== Producing: {topic} ===")
    script, meta = make_script(topic)
    audio = narrate(script)
    images = fetch_images(topic, IMAGE_COUNT)
    video = build_video(images, audio)
    with open(os.path.join(WORK, "meta.txt"), encoding="utf-8") as f:
        meta_text = f.read()
    if os.environ.get("NTY_UPLOAD", "true").lower() == "true":
        upload(video, meta_text)
    else:
        print("[main] NTY_UPLOAD=false — skipping upload. Video at", video)
    print("=== Done ===")


if __name__ == "__main__":
    main()
