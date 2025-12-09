[Setup]
AppName=NotesOverlay
AppVersion=1.10
DefaultDirName={pf}\NotesOverlay
OutputDir=C:\Users\btser\OneDrive\Documents\GitHub\Notes\Installers
OutputBaseFilename=NotesOverlay_1.10_Setup

[Files]
Source: "C:\Users\btser\OneDrive\Documents\GitHub\Notes\dist\NotesOverlay.exe"; DestDir: "{app}"; DestName: "NotesOverlay.exe"
Source: "C:\Users\btser\OneDrive\Documents\GitHub\Notes\app.ico"; DestDir: "{app}"

[Icons]
Name: "{commonprograms}\NotesOverlay"; Filename: "{app}\NotesOverlay.exe"; IconFilename: "{app}\app.ico"
Name: "{userdesktop}\NotesOverlay"; Filename: "{app}\NotesOverlay.exe"; IconFilename: "{app}\app.ico"