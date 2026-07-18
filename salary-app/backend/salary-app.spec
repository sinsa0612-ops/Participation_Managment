# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 빌드 스펙 — FastAPI 백엔드 + React 빌드(dist)를 onedir(폴더형)로 묶는다.

빌드: backend/ 에서  pyinstaller salary-app.spec --noconfirm --clean
산출물: backend/dist/salary-app/  (폴더 통째로 배포 또는 Inno Setup으로 setup.exe 생성)

onedir를 쓰는 이유:
  - onefile은 실행마다 %TEMP%에 압축을 풀어, 다른 PC의 백신·임시폴더 정책에 따라
    pydantic_core.pyd 같은 컴파일 확장모듈이 차단/검역되면 "실행은 되는데 기능이
    작동하지 않는" 증상이 난다. onedir는 파일이 디스크에 그대로 놓여 훨씬 안정적이고
    시작도 빠르며, 설치 마법사(setup.exe)로 감싸기에도 적합하다.
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

frontend_dist = os.path.join(SPECPATH, "..", "frontend", "dist")
if not os.path.isdir(frontend_dist):
    raise SystemExit(f"프론트엔드 빌드가 없습니다: {frontend_dist}\n먼저 `npm run build`를 실행하세요.")

# 프론트엔드 정적 파일을 frontend_dist 라는 이름으로 번들 (config.frontend_dir 와 일치)
datas = [(frontend_dist, "frontend_dist")]
binaries = []
# uvicorn은 프로토콜/루프 구현을 동적 import 하므로 서브모듈 전체 포함이 필요하다.
hiddenimports = collect_submodules("uvicorn")
hiddenimports += ["multipart", "python_multipart"]

# pydantic v2(컴파일된 pydantic_core)는 누락되면 전체가 실패하므로 명시 수집
for pkg in ("pydantic", "pydantic_core"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["main.py"],
    pathex=[SPECPATH],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir: 바이너리는 COLLECT가 폴더로 모은다
    name="salary-app",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="salary-app",
)
