#define MyAppName "Animus CLI"
#define MyAppVersion "1.0"
#define MyAppPublisher "Animus"
#define MyAppURL "https://github.com/yourusername/animus"
#define MyAppExeName "animus.bat"

[Setup]
AppId={{F4E7F482-1E04-4C2C-B038-F7A1C360D463}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
OutputDir=output
OutputBaseFilename=AnimusSetup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
SetupLogging=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application files
Source: "animus_cli\*"; DestDir: "{app}\animus_cli"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "powershell\*"; DestDir: "{app}\powershell"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "animus.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "run_animus.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; Create logs directory
[Dirs]
Name: "{app}\logs"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Add installation directory to PATH
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))
; Add compatibility flags to prevent UAC prompts
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"; ValueType: string; ValueName: "{app}\animus.bat"; ValueData: "RUNASADMIN"; Flags: uninsdeletevalue

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;

[Run]
; Create command-line wrapper in the installation directory
Filename: "cmd"; Parameters: "/c echo @echo off > ""{app}\animus.cmd"" && echo ""{app}\run_animus.bat"" %%* >> ""{app}\animus.cmd"""; Flags: runhidden

; Install Python dependencies
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""& {{pip install -r '{app}\requirements.txt'}}"""; Flags: runhidden; StatusMsg: "Installing Python dependencies..."
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove command-line wrapper
Filename: "cmd"; Parameters: "/c del ""{app}\animus.cmd"""; Flags: runhidden

[UninstallDelete]
Type: files; Name: "{app}\animus.cmd"
Type: filesandordirs; Name: "{app}\logs" 