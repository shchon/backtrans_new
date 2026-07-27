@echo off
chcp 65001 >nul

echo ========================================
echo   BackTranslate Dev Environment
echo ========================================
echo.

echo [1/2] Starting backend (FastAPI port 8765)...
start "BT-Backend" cmd /c "python -m uvicorn backend.main:app --port 8765 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting frontend (Vite port 5173)...
start "BT-Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================
echo   Backend : http://localhost:8765
echo   Frontend: http://localhost:5173
echo   Close the server windows to stop.
echo ========================================
echo.
pause
