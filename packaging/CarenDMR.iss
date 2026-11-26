; Inno-Setup-Skript für den CarenDMR-Installer (Inno Setup 6.3 oder neuer).
; Aufruf über packaging\build_release.ps1; dort werden AppVersion und
; SourceDir übergeben.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\release\dist\CarenDMR"
#endif

[Setup]
AppId={{6A237859-857C-4C03-B408-F86854C2B30B}
AppName=CarenDMR
AppVersion={#AppVersion}
AppVerName=CarenDMR {#AppVersion}
AppPublisher=Axel Baruschke, DK7EE
AppPublisherURL=https://github.com/AxBa1964/CarenDMR
AppSupportURL=https://github.com/AxBa1964/CarenDMR
DefaultDirName={autopf}\CarenDMR
DefaultGroupName=CarenDMR
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\release\installer
OutputBaseFilename=CarenDMR-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Installation ohne Administratorrechte möglich; auf Wunsch für alle Benutzer.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\CarenDMR.exe
UninstallDisplayName=CarenDMR

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung für CarenDMR anlegen"; GroupDescription: "Zusätzliche Verknüpfungen:"
Name: "desktopicon_easy"; Description: "Desktop-Verknüpfung für CarenDMR Easy (barrierefrei) anlegen"; GroupDescription: "Zusätzliche Verknüpfungen:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CarenDMR"; Filename: "{app}\CarenDMR.exe"; Parameters: "--gui"; Comment: "CarenDMR Hauptfenster"
Name: "{group}\CarenDMR Easy"; Filename: "{app}\CarenDMR.exe"; Parameters: "--easy"; Comment: "CarenDMR vereinfachte Bedienung"
Name: "{group}\CarenDMR TG-Monitor"; Filename: "{app}\CarenDMR.exe"; Parameters: "--tg-monitor"
Name: "{group}\CarenDMR deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CarenDMR"; Filename: "{app}\CarenDMR.exe"; Parameters: "--gui"; Tasks: desktopicon
Name: "{autodesktop}\CarenDMR Easy"; Filename: "{app}\CarenDMR.exe"; Parameters: "--easy"; Tasks: desktopicon_easy

[Run]
Filename: "{app}\CarenDMR.exe"; Parameters: "--gui"; Description: "CarenDMR jetzt starten"; Flags: nowait postinstall skipifsilent

; Hinweis: Einstellungen, Logbuch und Codec-Dateien liegen in
; %LOCALAPPDATA%\CarenDMR und bleiben bei der Deinstallation erhalten.
