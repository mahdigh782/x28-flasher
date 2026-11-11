; iscc /DSrc=<dist\x28-flasher> /DOut=<folder> /DVersion=<x.y.z> windows.iss
[Setup]
AppName=X28 Flasher
AppVersion={#Version}
AppPublisher=mralinp
DefaultDirName={autopf}\X28 Flasher
DefaultGroupName=X28 Flasher
OutputDir={#Out}
OutputBaseFilename=X28-Flasher-windows-x64-setup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "{#Src}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "{#Src}\..\MicrosoftEdgeWebview2Setup.exe"; Flags: dontcopy

[Icons]
Name: "{group}\X28 Flasher"; Filename: "{app}\X28 Flasher.exe"
Name: "{autodesktop}\X28 Flasher"; Filename: "{app}\X28 Flasher.exe"

[Code]
function WebView2Installed: Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(HKLM32, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version)
    and (Version <> '') and (Version <> '0.0.0.0');
  if not Result then
    Result := RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version)
      and (Version <> '') and (Version <> '0.0.0.0');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Code: Integer;
begin
  Result := '';
  if not WebView2Installed then begin
    ExtractTemporaryFile('MicrosoftEdgeWebview2Setup.exe');
    if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, Code)
      or not WebView2Installed then
      Result := 'Microsoft Edge WebView2 Runtime could not be installed. Connect to the internet, install WebView2 Runtime, and retry setup.';
  end;
end;
