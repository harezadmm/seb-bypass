@echo off
echo ================================================
echo   INSTALL SEB 3.10.2 FINAL PATCH
echo   - Bypass VM detection
echo   - Alt+Tab UNLOCK (Windows task switcher)
echo   - Tampilan fullscreen normal (tanpa minimize)
echo   - Screenshot diizinkan
echo   - Taskbar SEB bawah muncul
echo   - Tombol browser (Chrome) aktif
echo   - Tombol Power/Shutdown di taskbar aktif
echo ================================================
echo.
echo Menghentikan service Safe Exam Browser...
net stop SafeExamBrowser >nul 2>&1
taskkill /f /im SafeExamBrowser.exe >nul 2>&1
taskkill /f /im SafeExamBrowser.Client.exe >nul 2>&1
timeout /t 2 >nul

echo Menyalin semua file ke Program Files...

set SRC=%~dp0
set DEST=C:\Program Files\SafeExamBrowser\Application\

copy /Y "%SRC%SafeExamBrowser.exe"                            "%DEST%"
copy /Y "%SRC%SafeExamBrowser.Client.exe"                     "%DEST%"
copy /Y "%SRC%SafeExamBrowser.Configuration.dll"              "%DEST%"
copy /Y "%SRC%SafeExamBrowser.Monitoring.dll"                 "%DEST%"
copy /Y "%SRC%SafeExamBrowser.UserInterface.Desktop.dll"      "%DEST%"
copy /Y "%SRC%SafeExamBrowser.UserInterface.Mobile.dll"       "%DEST%"
copy /Y "%SRC%SafeExamBrowser.UserInterface.Shared.dll"       "%DEST%"

echo Memulai kembali service Safe Exam Browser...
net start SafeExamBrowser >nul 2>&1

if %errorlevel%==0 (
    echo.
    echo ================================================
    echo SUKSES! SEB 3.10.2 Final Patch ter-install.
    echo Alt+Tab sekarang membuka Windows task switcher.
    echo Jalankan SEB seperti biasa.
)
echo.
pause
