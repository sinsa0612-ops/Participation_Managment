@echo off
REM ============================================================
REM  인건비 배분 프로그램 — 설치 마법사(setup.exe) 빌드 스크립트
REM  결과물: installer\Output\salary-app-setup-1.0.0.exe
REM          (다른 PC에 이 setup.exe 하나만 전달 → 더블클릭 설치)
REM  요구사항: Node.js, uv(Python 3.12+), Inno Setup 6
REM ============================================================
chcp 65001 >nul
setlocal

echo [1/3] 프론트엔드 빌드 (React)...
cd /d "%~dp0frontend"
call npm install || goto :fail
call npm run build || goto :fail

echo [2/3] 백엔드 + 프론트 묶어서 폴더형(onedir) 빌드 (PyInstaller)...
cd /d "%~dp0backend"
call uv sync || goto :fail
call uv run pyinstaller salary-app.spec --noconfirm --clean || goto :fail

echo [3/3] 설치 마법사(setup.exe) 생성 (Inno Setup)...
cd /d "%~dp0"
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo [오류] Inno Setup 6 ^(ISCC.exe^)을 찾을 수 없습니다.
  echo        설치:  winget install JRSoftware.InnoSetup
  goto :fail
)
"%ISCC%" "installer\salary-app.iss" || goto :fail

echo.
echo ============================================================
echo  빌드 완료!  배포할 파일:
echo    %~dp0installer\Output\salary-app-setup-1.0.0.exe
echo  (다른 PC에 이 setup.exe 하나만 전달 후 더블클릭하면 설치됩니다)
echo ============================================================
pause
exit /b 0

:fail
echo.
echo [오류] 빌드 실패. 위 로그를 확인하세요.
pause
exit /b 1
