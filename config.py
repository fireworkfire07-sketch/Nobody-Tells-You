"""
config.py — Nobody Tells You
Tek yerden ayarlanabilen değerler. factory.py ve generate_script.py bunları
ortam değişkenlerinden okur; burada sadece referans/varsayılanları görürsün.
Değiştirmek için GitHub Actions secrets ya da workflow env kullan.
"""

DEFAULTS = {
    # Script
    "NTY_GROQ_MODEL": "llama-3.3-70b-versatile",
    "NTY_TARGET_WORDS": "1900",          # ~12-14 dk

    # Ses (belgesel tonu)
    "NTY_TTS_VOICE": "en-US-ChristopherNeural",
    "NTY_TTS_RATE": "-6%",
    "NTY_TTS_PITCH": "-2Hz",

    # Görsel
    "NTY_IMAGE_COUNT": "12",
    "NTY_IMAGE_STYLE": ("dark cinematic documentary still, muted desaturated tones, "
                        "dramatic lighting, film grain, moody, no text, no watermark"),

    # Yükleme
    "NTY_UPLOAD": "true",
    "NTY_PRIVACY": "private",             # ilk testlerde private tut
}
