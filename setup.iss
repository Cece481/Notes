[Setup]
AppName=Notesly
AppVersion=1.12
DefaultDirName={pf}\Notely
OutputDir=C:\Users\btser\OneDrive\Documents\GitHub\Notes\Installers
OutputBaseFilename=NotesOverlay_1.12_Setup

[Files]
Source: "C:\Users\btser\OneDrive\Documents\GitHub\Notes\dist\Notely.exe"; DestDir: "{app}"; DestName: "Notely.exe"
Source: "C:\Users\btser\OneDrive\Documents\GitHub\Notes\app.ico"; DestDir: "{app}"

[Icons]
Name: "{commonprograms}\Notely"; Filename: "{app}\Notely.exe"; IconFilename: "{app}\app.ico"
Name: "{userdesktop}\Notely"; Filename: "{app}\Notely.exe"; IconFilename: "{app}\app.ico"