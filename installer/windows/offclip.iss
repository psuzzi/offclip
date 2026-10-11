; offclip Windows installer (Inno Setup 6). Built by scripts/build-windows-installer.ps1:
;   ISCC.exe /DAppVersion=1.1.3 /DSourceDir=<staged tree> /DOutputDir=<dist> offclip.iss
; Per-user install, no administrator rights. The first start fetches what is missing into %LOCALAPPDATA%\offclip.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist"
#endif

[Setup]
AppId={{7E0E3F4B-5D2C-4B3A-9A2E-0FFC11C0FF11}
AppName=offclip
AppVersion={#AppVersion}
AppVerName=offclip {#AppVersion}
AppPublisher=Patrik Suzzi
AppPublisherURL=https://github.com/psuzzi/offclip
AppSupportURL=https://github.com/psuzzi/offclip/issues
AppUpdatesURL=https://github.com/psuzzi/offclip/releases
DefaultDirName={localappdata}\Programs\offclip
DefaultGroupName=offclip
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutputDir}
OutputBaseFilename=offclip-setup
SetupIconFile={#SourceDir}\assets\icon.ico
UninstallDisplayIcon={app}\offclip.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible or arm64
LicenseFile={#SourceDir}\LICENSE
CloseApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\offclip\*"; DestDir: "{app}\offclip"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc"
Source: "{#SourceDir}\scripts\bootstrap.ps1"; DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "{#SourceDir}\run.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\requirements-ffmpeg.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\assets\icon.ico"; DestDir: "{app}"; DestName: "offclip.ico"; Flags: ignoreversion

[Icons]
Name: "{group}\offclip"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; IconFilename: "{app}\offclip.ico"; Comment: "Save public audio and video clips for personal offline use"
Name: "{autodesktop}\offclip"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; IconFilename: "{app}\offclip.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\run.bat"; Description: "Start offclip now (the first start fetches what it needs)"; Flags: postinstall nowait skipifsilent shellexec

[UninstallDelete]
; the per-user data folder: private Python, venv, updated versions, settings, log. Downloads are elsewhere.
Type: filesandordirs; Name: "{localappdata}\offclip"
