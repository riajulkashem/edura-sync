; ============================================================================
; EduraSync – Inno Setup installer script
; Built by the windows-installer.yml workflow.
;
; Version is injected at build time:
;   ISCC.exe /DMyAppVersion="1.0.42" installer\setup.iss
; ============================================================================

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#define MyAppName       "EduraSync"
#define MyAppPublisher  "Softzenix IT"
#define MyAppURL        "https://softzenixbd.com"
#define MyAppSupportURL "https://softzenixbd.com/support"
#define MyAppExeName    "EduraSync.exe"
#define MyAppID         "EA3FCF1E-0EB9-4DEA-AB7A-ADE3D2B7AAF8"
#define MyAppCopyright  "Copyright © 2024 Softzenix IT. All rights reserved."

; ── [Setup] ──────────────────────────────────────────────────────────────────
[Setup]
AppId={#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppSupportURL}
AppUpdatesURL={#MyAppURL}
AppCopyright={#MyAppCopyright}

; Install location
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableProgramGroupPage=yes

; Wizard appearance
WizardStyle=modern
WizardSizePercent=120,110
WizardResizable=no
; Paths are relative to this .iss file (installer\), so no prefix needed for
; BMPs (same dir) and ..\ for assets one level up.
WizardImageFile=wizard_sidebar.bmp
WizardSmallImageFile=wizard_header.bmp
SetupIconFile=app_icon.ico

; Pages
DisableWelcomePage=no
DisableReadyPage=no
DisableFinishedPage=no

; Output — relative to this .iss file location (installer\), so "output"
; resolves to installer\output\ in the repo root.
OutputDir=output
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
InternalCompressLevel=ultra64

; Privileges & OS requirement
PrivilegesRequired=admin
MinVersion=10.0

; Uninstall info shown in Windows Add/Remove Programs
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
CreateUninstallRegKey=yes

; Restart behaviour
CloseApplications=yes
RestartApplications=no

; ── [Languages] ──────────────────────────────────────────────────────────────
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── [CustomMessages] ─────────────────────────────────────────────────────────
[CustomMessages]
english.WelcomeLabel1=Welcome to the [name] Setup Wizard
english.WelcomeLabel2=This will install [name/ver] on your computer.%n%nPlease close all other applications before continuing.
english.FinishedLabel=Setup has finished installing [name] on your computer.%n%nClick Finish to exit Setup.
english.FinishedHeadingLabel=Completing the [name] Setup Wizard

; ── [Tasks] ──────────────────────────────────────────────────────────────────
[Tasks]
Name: "desktopicon";  Description: "Create a &desktop shortcut";              GroupDescription: "Shortcuts:"
Name: "startmenu";    Description: "Create a &Start Menu entry";              GroupDescription: "Shortcuts:"
Name: "startup";      Description: "Launch {#MyAppName} when &Windows starts (system tray)"; GroupDescription: "On system start:"; Flags: unchecked

; ── [Files] ──────────────────────────────────────────────────────────────────
[Files]
; Main application bundle (produced by PyInstaller one-directory build)
Source: "..\dist\EduraSync\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── [Registry] ───────────────────────────────────────────────────────────────
[Registry]
; Add/Remove Programs extended info
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{{#MyAppID}_is1"; ValueType: string; ValueName: "DisplayVersion";   ValueData: "{#MyAppVersion}";         Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{{#MyAppID}_is1"; ValueType: string; ValueName: "Publisher";         ValueData: "{#MyAppPublisher}";        Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{{#MyAppID}_is1"; ValueType: string; ValueName: "URLInfoAbout";      ValueData: "{#MyAppURL}";              Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{{{#MyAppID}_is1"; ValueType: string; ValueName: "HelpLink";          ValueData: "{#MyAppSupportURL}";       Flags: uninsdeletevalue

; App settings key
Root: HKCU; Subkey: "Software\SoftzenixIT\{#MyAppName}"; ValueType: string; ValueName: "InstallDir"; ValueData: "{app}"; Flags: uninsdeletekey

; ── [Icons] ──────────────────────────────────────────────────────────────────
[Icons]
; Start Menu
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startmenu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}";        Tasks: startmenu

; Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

; Windows startup (runs minimised to tray)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--headless"; WorkingDir: "{app}"; Tasks: startup

; ── [Run] ────────────────────────────────────────────────────────────────────
[Run]
Filename: "{app}\{#MyAppExeName}"; \
  Description: "Launch {#MyAppName} now"; \
  Flags: nowait postinstall skipifsilent shellexec; \
  WorkingDir: "{app}"

; ── [UninstallRun] ───────────────────────────────────────────────────────────
[UninstallRun]
; Stop any running instance before uninstalling
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden waituntilterminated; RunOnceId: "KillApp"

; ── [Code] ───────────────────────────────────────────────────────────────────
[Code]

// ── Wizard font & colour polish ──────────────────────────────────────────────
procedure InitializeWizard();
begin
  // Apply Segoe UI across the whole wizard
  WizardForm.Font.Name := 'Segoe UI';
  WizardForm.Font.Size := 9;

  // Welcome page heading
  WizardForm.WelcomeLabel1.Font.Name := 'Segoe UI';
  WizardForm.WelcomeLabel1.Font.Size := 14;
  WizardForm.WelcomeLabel1.Font.Style := [fsBold];

  // Finish page heading
  WizardForm.FinishedHeadingLabel.Font.Name := 'Segoe UI';
  WizardForm.FinishedHeadingLabel.Font.Size := 14;
  WizardForm.FinishedHeadingLabel.Font.Style := [fsBold];

  // Inner-page header title
  WizardForm.PageNameLabel.Font.Name := 'Segoe UI';
  WizardForm.PageNameLabel.Font.Size := 11;
  WizardForm.PageNameLabel.Font.Style := [fsBold];
end;

// ── Prevent downgrade ────────────────────────────────────────────────────────
function InitializeSetup(): Boolean;
var
  sUninstallKey, sInstalledVer: String;
begin
  Result := True;
  sUninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
                   '{' + '{#MyAppID}' + '}_is1';
  if RegQueryStringValue(HKLM, sUninstallKey, 'DisplayVersion', sInstalledVer) then
  begin
    if CompareStr(sInstalledVer, '{#MyAppVersion}') > 0 then
    begin
      MsgBox('A newer version of {#MyAppName} (' + sInstalledVer + ') is already ' +
             'installed. Please uninstall it first.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

// ── Offer to launch at finish ─────────────────────────────────────────────────
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;
