@echo off
cd /d "%~dp0"

python main.py

if %errorlevel% neq 0 (
    echo.
    echo Co loi xay ra! Bam phim bat ky de xem...
    pause
)