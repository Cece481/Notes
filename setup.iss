[Setup]
AppName=Notely
AppVersion=2.1
DefaultDirName={pf}\Notely
OutputDir=C:\Users\btser\OneDrive\Documents\GitHub\Notes\Installers
OutputBaseFilename=Notey_2.1_Setup.exe

[Files]
Source: "C:\Users\btser\OneDrive\Documents\GitHub\Notes\dist\Notely.exe"; DestDir: "{app}"; DestName: "Notely.exe"
Source: "C:\Users\btser\OneDrive\Documents\GitHub\Notes\app.ico"; DestDir: "{app}"

[Icons]
Name: "{commonprograms}\Notely"; Filename: "{app}\Notely.exe"; IconFilename: "{app}\app.ico"
Name: "{userdesktop}\Notely"; Filename: "{app}\Notely.exe"; IconFilename: "{app}\app.ico"