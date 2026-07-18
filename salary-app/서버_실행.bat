@echo off
chcp 65001 > nul
title 사업비 인건비 배분 앱
setlocal EnableDelayedExpansion

set NEED_RESTART=0

echo.
echo  ====================================
echo   사업비 인건비 배분 앱 서버 시작
echo  ====================================
echo.

:: ────────────────────────────────
::  [1/2] uv 설치 확인
:: ────────────────────────────────
echo  [1/2] uv (Python 패키지 관리자) 확인 중...
where uv > nul 2>&1
if %errorlevel% neq 0 (
    echo       설치되어 있지 않습니다. 설치를 시작합니다...
    echo.
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo.
        echo  [오류] uv 설치에 실패했습니다.
        echo         수동 설치: https://docs.astral.sh/uv/getting-started/installation/
        pause & exit /b 1
    )
    echo.
    echo       uv 설치 완료.
    set NEED_RESTART=1
) else (
    for /f "tokens=*" %%v in ('uv --version 2^>nul') do echo       확인됨: %%v
)

:: ────────────────────────────────
::  [2/2] Node.js 설치 확인
:: ────────────────────────────────
echo  [2/2] Node.js 확인 중...
where node > nul 2>&1
if %errorlevel% neq 0 (
    echo       설치되어 있지 않습니다. winget으로 설치를 시작합니다...
    echo.
    where winget > nul 2>&1
    if %errorlevel% neq 0 (
        echo  [오류] winget을 찾을 수 없습니다.
        echo         Node.js 수동 설치: https://nodejs.org/
        echo         설치 후 이 파일을 다시 실행하세요.
        pause & exit /b 1
    )
    winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements --silent
    if %errorlevel% neq 0 (
        echo.
        echo  [오류] Node.js 설치에 실패했습니다.
        echo         수동 설치: https://nodejs.org/
        pause & exit /b 1
    )
    echo.
    echo       Node.js 설치 완료.
    set NEED_RESTART=1
) else (
    for /f "tokens=*" %%v in ('node --version 2^>nul') do echo       확인됨: Node.js %%v
)

:: ────────────────────────────────
::  새로 설치한 경우 PATH 갱신
:: ────────────────────────────────
if %NEED_RESTART%==1 (
    echo.
    echo  환경변수 PATH를 갱신합니다...
    for /f "skip=2 tokens=2,*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"
    for /f "skip=2 tokens=2,*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%b"
    set "PATH=!SYS_PATH!;!USER_PATH!"
    echo  PATH 갱신 완료.
)

echo.
echo  ────────────────────────────────────
echo   서버를 시작합니다...
echo  ────────────────────────────────────

:: ────────────────────────────────
::  백엔드 실행
:: ────────────────────────────────
start "백엔드 (FastAPI:8001)" cmd /k "cd /d D:\AI\business_management\salary-app\backend && uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

:: ────────────────────────────────
::  프론트엔드 실행 (최초 npm install 포함)
:: ────────────────────────────────
start "프론트엔드 (Vite:5173)" cmd /k "cd /d D:\AI\business_management\salary-app\frontend && npm install && npm run dev"

echo.
echo  ====================================
echo   서버가 시작되었습니다!
echo  ====================================
echo.
echo    프론트엔드  ->  http://localhost:5173
echo    백엔드 API  ->  http://localhost:8001
echo    API 문서    ->  http://localhost:8001/docs
echo.
echo   서버 종료: 각 창에서 Ctrl+C 를 누르세요.
echo.
pause
