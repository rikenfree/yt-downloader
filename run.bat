@echo off
echo ==============================================
echo YouTube Downloader GUI Startup
echo ==============================================
echo.
echo Checking and updating requirements...
pip install --upgrade yt-dlp
pip install -r requirements.txt
echo.
echo Starting YouTube Downloader...
python yt_downloader.py
pause
