#define MyAppName "Animus CLI"
#define MyAppVersion "1.0"
#define MyAppPublisher "Animus"
#define MyAppURL "https://github.com/markkroening/Animus"
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
; Silent installation support
DisableWelcomePage=no
DisableReadyPage=no
DisableFinishedPage=no
AllowNoIcons=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy entire animus_cli directory with its structure intact
Source: "animus_cli\*"; DestDir: "{app}\animus_cli"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "animus.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall_cleanup.bat"; DestDir: "{app}"; Flags: ignoreversion
; Exclude set_api_key.bat from installer

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Add installation directory to PATH
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\Animus"

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

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    Exec(ExpandConstant('{app}\uninstall_cleanup.bat'), '', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

[Run]
; Install Python dependencies
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""& {{pip install -r '{app}\requirements.txt'}}"""; Flags: runhidden; StatusMsg: "Installing Python dependencies..."
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent 