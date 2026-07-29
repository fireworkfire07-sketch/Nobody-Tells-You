import io, os, re, time, shutil, asyncio, subprocess, requests, urllib.parse
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

VOICE = "en-US-GuyNeural"   # ciddi, otoriter, "nobody tells you" anlatici tonu
RATE = "-3%"                 # hafif yavas ama gergin tempo

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

def paragraflar():
    with open("script.txt", encoding="utf-8") as f:
        text = f.read()
    return [p.strip() for p in text.split("\n\n") if p.strip()]

async def _seslendir(text, out):
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(out)

def seslendir(text, out, deneme=5):
    for i in range(deneme):
        try:
            asyncio.run(_seslendir(text, out))
            if os.path.exists(out) and os.path.getsize(out) > 1000:
                return
            raise ValueError("ses dosyasi bos")
        except Exception as e:
            print(f"Ses deneme {i+1}/{deneme} hata: {e}")
            time.sleep(10 * (i + 1))
    raise SystemExit(f"Ses uretilemedi: {out}")

def gorsel_uret(prompt, out, deneme=5):
    p = urllib.parse.quote(f"{prompt}, cinematic dark documentary style, noir lighting, conspiracy thriller atmosphere, high contrast")
    url = f"https://image.pollinations.ai/prompt/{p}?width=1280&height=720&nologo=true"
    for i in range(deneme):
        try:
            r = requests.get(url, timeout=120)
            if r.ok and len(r.content) > 10000:
                open(out, "wb").write(r.content)
                return True
            raise ValueError(f"kotu cevap: {r.status_code}, {len(r.content)} byte")
        except Exception as e:
            print(f"Gorsel deneme {i+1}/{deneme} hata: {e}")
            time.sleep(15 * (i + 1))
    return False

def sure(dosya):
    r = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration",
                        "-of","csv=p=0", dosya], capture_output=True, text=True)
    return float(r.stdout.strip())

def sahne_video(img, ses, out):
    d = sure(ses)
    # Ken Burns: yavas zoom
    vf = (f"scale=1600:900,zoompan=z='min(zoom+0.0008,1.15)':d={int(d*25)}"
          f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps=25")
    subprocess.run(["ffmpeg","-y","-loop","1","-i",img,"-i",ses,
                    "-vf",vf,"-c:v","libx264","-c:a","aac","-shortest",
                    "-pix_fmt","yuv420p", out], check=True)

def birlestir(parcalar, out):
    with open("liste.txt","w") as f:
        for p in parcalar:
            f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i","liste.txt",
                    "-c","copy", out], check=True)

def thumbnail_metni(meta_satirlari):
    for satir in meta_satirlari:
        if satir.strip().upper().startswith("THUMBNAIL:"):
            metin = satir.split(":", 1)[1].strip()
            if metin:
                return metin
    baslik = meta_satirlari[0] if meta_satirlari else ""
    kelimeler = baslik.split()[:5]
    return " ".join(kelimeler) if kelimeler else "Nobody Tells You"

def _thumbnail_font(boyut):
    for yol in FONT_CANDIDATES:
        if os.path.exists(yol):
            return ImageFont.truetype(yol, boyut)
    return ImageFont.load_default()

def _satirlara_böl(cizim, metin, font, max_genislik):
    kelimeler = metin.upper().split()
    satirlar = []
    mevcut = ""
    for kelime in kelimeler:
        aday = f"{mevcut} {kelime}".strip()
        genislik = cizim.textbbox((0, 0), aday, font=font)[2]
        if genislik <= max_genislik or not mevcut:
            mevcut = aday
        else:
            satirlar.append(mevcut)
            mevcut = kelime
    if mevcut:
        satirlar.append(mevcut)
    return satirlar

def thumbnail_uret(metin, out="thumbnail.jpg", deneme=5):
    p = urllib.parse.quote(
        f"{metin}, cinematic dark documentary style, noir lighting, "
        "conspiracy thriller atmosphere, high contrast, dramatic"
    )
    url = f"https://image.pollinations.ai/prompt/{p}?width=1280&height=720&nologo=true"
    arka_plan = None
    for i in range(deneme):
        try:
            r = requests.get(url, timeout=120)
            if r.ok and len(r.content) > 10000:
                arka_plan = Image.open(io.BytesIO(r.content)).convert("RGB").resize((1280, 720))
                break
            raise ValueError(f"kotu cevap: {r.status_code}, {len(r.content)} byte")
        except Exception as e:
            print(f"Thumbnail arka plani deneme {i+1}/{deneme} hata: {e}")
            time.sleep(15 * (i + 1))
    if arka_plan is None:
        print("Thumbnail arka plani uretilemedi, duz renkli zemin kullaniliyor")
        arka_plan = Image.new("RGB", (1280, 720), (18, 18, 18))

    cizim = ImageDraw.Draw(arka_plan)
    boyut = 130
    satirlar = [metin.upper()]
    while boyut > 40:
        font = _thumbnail_font(boyut)
        satirlar = _satirlara_böl(cizim, metin, font, 1150)
        satir_yuksekligi = boyut + 20
        if len(satirlar) <= 3 and len(satirlar) * satir_yuksekligi <= 600:
            break
        boyut -= 10
    font = _thumbnail_font(boyut)
    satir_yuksekligi = boyut + 20
    toplam_yukseklik = len(satirlar) * satir_yuksekligi
    y = (720 - toplam_yukseklik) // 2

    overlay = Image.new("RGBA", arka_plan.size, (0, 0, 0, 0))
    overlay_cizim = ImageDraw.Draw(overlay)
    overlay_cizim.rectangle(
        [(0, max(0, y - 30)), (1280, min(720, y + toplam_yukseklik + 10))],
        fill=(0, 0, 0, 130),
    )
    arka_plan = Image.alpha_composite(arka_plan.convert("RGBA"), overlay).convert("RGB")
    cizim = ImageDraw.Draw(arka_plan)

    for satir in satirlar:
        genislik = cizim.textbbox((0, 0), satir, font=font)[2]
        x = (1280 - genislik) // 2
        cizim.text(
            (x, y),
            satir,
            font=font,
            fill="white",
            stroke_width=max(4, boyut // 20),
            stroke_fill="black",
        )
        y += satir_yuksekligi

    arka_plan.save(out, "JPEG", quality=92)
    return out

def yukle(video, thumbnail=None):
    with open("meta.txt", encoding="utf-8") as f:
        satirlar = f.read().strip().split("\n")
    baslik = satirlar[0][:100]
    aciklama = "\n".join(satirlar[1:])[:4900]
    creds = Credentials(None,
        refresh_token=os.environ["NTY_REFRESH_TOKEN"],
        client_id=os.environ["NTY_CLIENT_ID"],
        client_secret=os.environ["NTY_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token")
    yt = build("youtube","v3",credentials=creds)
    body = {"snippet":{"title":baslik,"description":aciklama,
                       "categoryId":"27","defaultLanguage":"en"},
            "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False,
                      "containsSyntheticMedia":True}}
    req = yt.videos().insert(part="snippet,status", body=body,
            media_body=MediaFileUpload(video, resumable=True))
    res = req.execute()
    video_id = res["id"]
    print("Yuklendi:", "https://youtu.be/" + video_id)

    if thumbnail and os.path.exists(thumbnail):
        try:
            yt.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail)).execute()
            print("Thumbnail ayarlandi.")
        except HttpError as e:
            print(f"UYARI: thumbnail ayarlanamadi (kanal dogrulanmamis olabilir, HTTP {e.status_code}): {e}")
        except Exception as e:
            print(f"UYARI: thumbnail ayarlanirken beklenmeyen hata: {e}")

    return video_id

def main():
    sahneler = paragraflar()
    parcalar = []
    onceki_img = None
    for i, p in enumerate(sahneler):
        ses = f"s{i}.mp3"; img = f"s{i}.jpg"; vid = f"s{i}.mp4"
        seslendir(p, ses)
        prompt = re.sub(r"[^a-zA-Z0-9 ]", "", p)[:150]
        if not gorsel_uret(prompt, img):
            if onceki_img:
                print(f"Sahne {i+1}: gorsel uretilemedi, onceki gorsel kullaniliyor")
                shutil.copy(onceki_img, img)
            else:
                raise SystemExit(f"Gorsel uretilemedi: sahne {i}")
        onceki_img = img
        sahne_video(img, ses, vid)
        parcalar.append(vid)
        print(f"Sahne {i+1}/{len(sahneler)} tamam")
    birlestir(parcalar, "final.mp4")
    print("Video hazir: final.mp4")

    with open("meta.txt", encoding="utf-8") as f:
        meta_satirlari = f.read().strip().split("\n")
    thumb_metni = thumbnail_metni(meta_satirlari)
    thumbnail_uret(thumb_metni, "thumbnail.jpg")
    print(f"Thumbnail hazir: thumbnail.jpg ('{thumb_metni}')")

    if os.environ.get("SKIP_YOUTUBE_UPLOAD", "").lower() in {"1", "true", "yes"}:
        print("YouTube upload skipped for test run.")
        return

    required = ["NTY_CLIENT_ID", "NTY_CLIENT_SECRET", "NTY_REFRESH_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit(f"Missing YouTube secrets: {', '.join(missing)}")
    yukle("final.mp4", "thumbnail.jpg")

if __name__ == "__main__":
    main()
