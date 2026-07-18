; ============================================================
;  인건비 배분 프로그램 — Inno Setup 설치 마법사 스크립트
;  PyInstaller onedir 산출물(..\backend\dist\salary-app)을 setup.exe 하나로 감싼다.
;  빌드:  "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer\salary-app.iss
;  산출물: installer\Output\salary-app-setup-<버전>.exe
; ============================================================

#define MyAppName "인건비 배분 프로그램"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "사업관리"
#define MyAppExeName "salary-app.exe"
; PyInstaller onedir 결과 폴더 (이 스크립트 기준 상대경로)
#define DistDir "..\backend\dist\salary-app"

[Setup]
; AppId는 업그레이드 시 같은 앱으로 인식되도록 고정한다(변경 금지).
AppId={{B2F1B0E2-7A3C-4E1A-9C2D-5F6A8B9C0D11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; 관리자 권한 없이 설치되도록 사용자 영역(%LOCALAPPDATA%)에 설치한다.
DefaultDirName={localappdata}\Programs\salary-app
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
; 64비트 윈도우 전용 (PyInstaller가 x64로 빌드됨)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=salary-app-setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 업그레이드 설치 시 실행 중인 앱을 자동으로 닫는다.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; onedir 폴더 전체(exe + _internal/*)를 설치 폴더로 복사한다.
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 설치 직후 바로 실행할 수 있도록 옵션 제공.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; 참고: 사용자 데이터(DB)는 설치 폴더가 아니라 %LOCALAPPDATA%\salary-app 에 저장되므로,
;       프로그램을 제거해도 데이터는 보존된다. 데이터까지 지우려면 그 폴더를 수동 삭제.
