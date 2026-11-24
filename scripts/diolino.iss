; Standard native installation engine; no shell scripts or child processes.
#ifndef AppVersion
  #error AppVersion must be supplied by build_distribution.ps1
#endif
#define AppSource "..\releases\" + AppVersion + "\Diolino"

[Setup]
AppId={{E9264D62-A9E0-4CE9-AF4C-AB130DAC705A}
AppName=Diolino
AppVersion={#AppVersion}
AppPublisher=Diolino
DefaultDirName={localappdata}\Programs\Diolino\{#AppVersion}
DefaultGroupName=Diolino
UsePreviousAppDir=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\releases\{#AppVersion}-distribuicao
OutputBaseFilename=Diolino-Instalador
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Diolino.exe
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"
Name: "startup"; Description: "Iniciar minimizado com o Windows"

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Diolino"; Filename: "{app}\Diolino.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Diolino"; Filename: "{app}\Diolino.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\Diolino"; Filename: "{app}\Diolino.exe"; Parameters: "--background"; WorkingDir: "{app}"; Tasks: startup

#include "uninstall_cleanup.iss"
