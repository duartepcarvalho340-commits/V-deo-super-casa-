"""Finalize the Day-1 Reel after the close: voice, audio, final render, cover, story, caption. Run from reel/."""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT = os.path.dirname(ROOT)
N = json.load(open(f"{ROOT}/numbers.json")); RECORD = 7818.93
def sh(c): print(">", c); subprocess.run(c, shell=True, check=True, cwd=ROOT)
sh("python3 code/voice_en.py")
sh("python3 code/audio.py && ffmpeg -loglevel error -y -i audio/stems/mix_raw.wav -af loudnorm=I=-14:TP=-1:LRA=11 -ar 48000 audio/mix.wav")
sh("python3 code/render.py --scale 1 --out previews/cov.png --still 15.0")
from PIL import Image, ImageDraw, ImageFont, ImageFilter
F = f"{ROOT}/assets/fonts/"
c = Image.open(f"{ROOT}/previews/cov_15.00.png").convert("RGB"); c.save(f"{OUT}/cover.jpg", quality=92)
W, H = 1080, 1920; im = Image.new("RGB", (W, H), "#FAFAF7"); d = ImageDraw.Draw(im)
cw = 600; ch = int(1920 * cw / 1080); s = c.resize((cw, ch), Image.LANCZOS); x = (W - cw) // 2; y = 420
shd = Image.new("RGBA", (cw + 60, ch + 60), (0, 0, 0, 0)); ImageDraw.Draw(shd).rectangle([30, 30, cw + 30, ch + 30], fill=(0, 0, 0, 60)); shd = shd.filter(ImageFilter.GaussianBlur(14))
im.paste(shd, (x - 22, y - 18), shd); im.paste(s, (x, y)); d.rectangle([x, y, x + cw, y + ch], outline="#141414", width=4)
pf = ImageFont.truetype(F + "Inter-Bold.otf", 40); t = "NEW REEL ▶ WATCH IT ON OUR PROFILE"; tw = d.textlength(t, font=pf)
d.rounded_rectangle([(W - tw) / 2 - 40, 290, (W + tw) / 2 + 40, 380], radius=45, fill="#C8102E"); d.text((W / 2, 335), t, font=pf, fill="white", anchor="mm")
q1 = ImageFont.truetype(F + "Fraunces-800.ttf", 58); q2 = ImageFont.truetype(F + "Inter-Bold.otf", 40)
d.text((W / 2, y + ch + 80), "Worst behind us, or ahead?", font=q1, fill="#141414", anchor="mm")
d.text((W / 2, y + ch + 150), "Comment BEHIND or AHEAD", font=q2, fill="#1B7F4B", anchor="mm")
im.save(f"{OUT}/story.jpg", quality=92)
up = N["sp"] > 0; fr = (1 - N["sp_close"] / RECORD) * 100
p = lambda v: f"{'+' if v > 0 else '-'}{abs(v):.1f}%"
verdict = (("A relief rally. But one green day doesn't end a correction." if fr >= 10 else "A relief rally, strong enough to lift the S&P 500 out of correction territory, for now.")
           if up else "No relief: the S&P 500 logged its 8th straight loss.")
cap = f"""Day 1 after Wall Street's brutal week. Does the market still have a pulse? 🫀

Monday's close (Nov 23):
• S&P 500: {p(N['sp'])}
• Nasdaq: {p(N['ndq'])}
• Dow: {'+' if N['dow_pts'] > 0 else '-'}{abs(int(round(N['dow_pts']))):,} points
• Nvidia: {p(N['nvda'])}, after Friday's -14% on a report of an SEC review of its accounting

{verdict}

Zoom out: the S&P 500 is still about {fr:.1f}% below its Oct 6 record close.

Next up: Dell's earnings Tuesday after the close, and October PCE inflation Wednesday at 8:30 ET.

One day is not a trend. Long-term investors watch the direction, not the noise.

Your call: is the worst behind us, or still ahead? Comment BEHIND or AHEAD 👇

Follow @panic.and.profit for markets, macro and geopolitics without the noise.

Not financial advice.

#StockMarket #SP500 #Nasdaq #Nvidia #Investing"""
open(f"{OUT}/caption.txt", "w").write(cap)
sh("python3 code/render.py --scale 1 --fps 60 --out ../reel.mp4")
sh("ffmpeg -loglevel error -y -i ../reel.mp4 -vf scale=540:-2 -r 30 -c:a aac ../preview.mp4")
print("FINALIZED")
