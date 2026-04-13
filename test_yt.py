import yt_dlp
ydl_opts = {"js_runtimes": ["node"], "quiet": True}
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("Success")
except Exception as e:
    print("Error:", e)
