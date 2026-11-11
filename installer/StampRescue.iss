; installer/StampRescue.iss — установщик StampRescue v0.5 (Inno Setup 6)
; Сборка:  "<LocalAppData>\Programs\Inno Setup 6\ISCC.exe" installer\StampRescue.iss
#define AppName    "StampRescue"
#define AppVersion "0.5"

[Setup]
AppId={{8F3A6C1D-2026-4B7E-9A11-510E20260111}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion} — Sirmik Edition
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
#ifdef OUTBASE
  #define OutBase OUTBASE
#else
  #define OutBase "StampRescue-" + AppVersion + "-setup"
#endif
OutputBaseFilename={#OutBase}
SetupIconFile=..\assets\app.ico
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppName}.exe
#ifndef Compression
  #define Comp "lzma2/max"
#else
  #define Comp LZMA
#endif
Compression={#Comp}
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ShowLanguageDialog=no

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; вся сборка PyInstaller (exe + _internal с моделью lama.onnx, Qt, пресетами, assets)
Source: "..\dist\StampRescue\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; редактируемая копия типовых пресетов рядом с exe (программа ищет их в первую очередь)
Source: "..\presets\*"; DestDir: "{app}\presets"; Flags: recursesubdirs createallsubdirs ignoreversion
; документация
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppName}.exe"
Name: "{group}\README (инструкция)"; Filename: "{app}\README.md"; Tasks: desktopicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\README.md"; Description: "Открыть инструкцию"; Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}\result"
Type: files; Name: "{app}\crash_log.txt"
Type: files; Name: "{app}\*.log"
