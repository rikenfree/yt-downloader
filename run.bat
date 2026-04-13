@echo off
echo ==============================================
echo YouTube Downloader GUI Startup
echo ==============================================
echo.
echo Checking and installing missing requirements...
pip install -r requirements.txt
echo.
echo Starting YouTube Downloader...
python yt_downloader.py
pause
