# Nobody-Tells-You

## Ne işe yarar

"Nobody Tells You" YouTube kanalı için ciddi/otoriter tonda, para/hayat/insan davranışı üzerine faceless (yüzsüz) video üreten ve yayınlayan otomasyon. Konuyu ya `shp-engine` reposu yollar ya da elle girilir; script, seslendirme, görsel, thumbnail ve YouTube upload'ı bu repo tek başına yapar.

## Pipeline akışı

```
Konu (repository_dispatch new_topic'ten VEYA manuel "topic" girdisinden, bos ise DEFAULT_TOPIC)
   → nty_engine.py   [Groq: llama-3.3-70b-versatile]
        script.txt (90-140 kisa "beat"), meta.txt (baslik/aciklama/hashtag) uretir
   → pipeline.py
        her sahne (beat) icin:
          seslendir()   [edge-tts, en-US-GuyNeural]                → s{i}.mp3
          gorsel_uret() [pollinations.ai, noir/komplo-belgeseli stili] → s{i}.jpg
          sahne_video() [ffmpeg, Ken Burns zoom]                    → s{i}.mp4
        birlestir()     [ffmpeg concat]                             → final.mp4
        thumbnail_metni()+thumbnail_uret() [pollinations.ai + Pillow] → thumbnail.jpg
        (upload acıksa) yukle() [YouTube Data API v3]
          → final.mp4 upload + thumbnails().set(thumbnail.jpg)
          → status.containsSyntheticMedia = true
```

Görsel/ses üretimi tamamen ücretsiz araçlarla (edge-tts, pollinations.ai) yapılır — ücretli bir API'ye geçilmez.

## Workflow'lar

| Dosya | Ne yapar | Nasıl tetiklenir |
|---|---|---|
| `produce.yml` (Video Uret ve Yukle) | Yukarıdaki tüm üretim zincirini çalıştırır | `repository_dispatch` (`new_topic`, `shp-engine`'den — upload otomatik açılır) **veya** manuel (`topic` opsiyonel, `upload_to_youtube` girdisiyle) |

Bu repoda `secret-history-plants`'ın aksine ayrı bir `claude.yml` (issue/PR yorumu ile Claude Code tetikleme) yok.

## Gerekli secret'lar

Değerler burada **asla** yazılmaz — sadece isim ve amaç. Repo → Settings → Secrets and variables → Actions.

| Secret | Ne işe yarar | Zorunlu mu |
|---|---|---|
| `GROQ_API_KEY` | `nty_engine.py` — script/meta üretimi | Evet |
| `NTY_YT_CLIENT_ID`, `NTY_YT_CLIENT_SECRET`, `NTY_YT_REFRESH_TOKEN` | `pipeline.py` — YouTube OAuth, video + thumbnail upload | Yalnızca `upload_to_youtube: true` iken |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Workflow başarısız olunca bildirim | Opsiyonel — yoksa adım sessizce atlanır |

**Uyarı:** Google Cloud OAuth consent screen **"In production"** olmalı. "Testing" modunda refresh token 7 günde geçersiz olur ve upload sessizce başarısız olur.

## Manuel çalıştırma

GitHub'da **Actions** → **Video Uret ve Yukle** → **Run workflow** → `topic` gir (boş bırakırsan `nty_engine.py` içindeki varsayılan konu kullanılır), gerçekten YouTube'a yüklensin istiyorsan `upload_to_youtube` kutusunu işaretle.

> **Not:** "Re-run" o an `main` branch'inde olan kodu çalıştırır, workflow'un ilk çalıştığı tarihteki kodu değil.

`upload_to_youtube: false` ile çalıştırırsan hiçbir şey YouTube'a gitmez; script+ses+görsel+thumbnail+render yine de üretilir ve Actions run'ının "Artifacts" bölümünden indirilebilir.

## Bilinen notlar / sorunlar

- `nty_engine.py`'nin ürettiği `meta.txt`'te `THUMBNAIL:` alanı yok (secret-history-plants'ın aksine) — bu yüzden `thumbnail_metni()` her zaman başlıktan ilk 3-5 kelimeyi türetir. Kasıtlı bir tasarım farkı, hata değil.
- Bu repo bugün uçtan uca test edildi (`upload_to_youtube: false`, konu: "Why nobody warns you about comparison") ve **tamamen başarılı** oldu — script, ses, görsel, render ve thumbnail üretimi çalışıyor. `secret-history-plants`'ta görülen "az sahne" hatası burada görülmedi.
- Gerçek bir YouTube upload'ı veya `thumbnails().set()` çağrısı bu incelemede test edilmedi (upload her zaman kapalı test edildi).
