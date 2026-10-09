param(
    [ValidateSet('Navigate','Capture','Fill','Submit','Ask','Refresh','Escape')][string]$Action = 'Capture',
    [string]$Url = 'http://127.0.0.1:8501',
    [string]$ValueFile,
    [string]$ScreenshotPath = "$PSScriptRoot\..\submission\06_Demo\screenshots\campus-ui-current.png",
    [int]$WaitSeconds = 0
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class CampusServiceBrowser {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int command);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int left, top, right, bottom; }
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort vk, scan; public uint flags, time; public UIntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public KEYBDINPUT key; }
  [DllImport("user32.dll", SetLastError=true)] static extern uint SendInput(uint n, INPUT[] input, int size);
  public static void TypeText(string value) {
    foreach (char c in value) {
      INPUT down=new INPUT(); down.type=1; down.key.scan=c; down.key.flags=4;
      INPUT up=down; up.key.flags=6;
      if (SendInput(2,new INPUT[]{down,up},Marshal.SizeOf(typeof(INPUT)))!=2) throw new Exception("Unicode keyboard input failed.");
    }
  }
  public static void Click(int x, int y) {
    SetCursorPos(x,y);
    mouse_event(2,0,0,0,UIntPtr.Zero);
    mouse_event(4,0,0,0,UIntPtr.Zero);
  }
  [DllImport("user32.dll")] static extern void mouse_event(uint f,uint x,uint y,uint data,UIntPtr extra);
}
'@
[void][CampusServiceBrowser]::SetProcessDPIAware()
if ($Action -eq 'Navigate') {
    if ($Url -notmatch '^http://127\.0\.0\.1:8501/?([?#].*)?$') { throw 'Only the local campus-service Streamlit page may be opened.' }
    Start-Process $Url
    Start-Sleep -Seconds 8
}
$browser = $null
for ($attempt=0; $attempt -lt 20; $attempt++) {
    $browser = Get-Process chrome,msedge -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -match '127\.0\.0\.1:8501|localhost:8501|校园智能客服助手' } |
        Select-Object -First 1
    if ($browser) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $browser) { throw 'No visible Edge window for the local campus-service page was found; no input was sent.' }
[void][CampusServiceBrowser]::ShowWindow($browser.MainWindowHandle, 3)
[void][CampusServiceBrowser]::SetForegroundWindow($browser.MainWindowHandle)
Start-Sleep -Milliseconds 500
if ($Action -in @('Fill','Ask')) {
    if (-not $ValueFile -or -not (Test-Path -LiteralPath $ValueFile)) { throw "$Action requires an existing ValueFile." }
    $rect = New-Object CampusServiceBrowser+RECT
    if (-not [CampusServiceBrowser]::GetWindowRect($browser.MainWindowHandle, [ref]$rect)) { throw 'Could not read the Edge window bounds.' }
    $centerX = [int](($rect.left + $rect.right) / 2)
    $inputY = [int]($rect.bottom - 135)
    [CampusServiceBrowser]::Click($centerX, $inputY)
    Start-Sleep -Milliseconds 700
    $text = Get-Content -LiteralPath $ValueFile -Raw -Encoding UTF8
    [System.Windows.Forms.Clipboard]::SetText($text)
    [System.Windows.Forms.SendKeys]::SendWait('^v')
    Start-Sleep -Milliseconds 700
    if ($Action -eq 'Ask') {
        [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
        if ($WaitSeconds -gt 0) { Start-Sleep -Seconds $WaitSeconds }
    }
} elseif ($Action -eq 'Refresh') {
    [System.Windows.Forms.SendKeys]::SendWait('^r')
    if ($WaitSeconds -gt 0) { Start-Sleep -Seconds $WaitSeconds }
} elseif ($Action -eq 'Escape') {
    [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
} elseif ($Action -eq 'Submit') {
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    if ($WaitSeconds -gt 0) { Start-Sleep -Seconds $WaitSeconds }
}
$rect = New-Object CampusServiceBrowser+RECT
if (-not [CampusServiceBrowser]::GetWindowRect($browser.MainWindowHandle, [ref]$rect)) { throw 'Could not read the Edge window bounds.' }
$width = $rect.right - $rect.left
$height = $rect.bottom - $rect.top
if ($width -lt 800 -or $height -lt 600) { throw "Browser window is too small for evidence capture ($width x $height)." }
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.CopyFromScreen($rect.left, $rect.top, 0, 0, $bitmap.Size)
    $directory = Split-Path -Parent $ScreenshotPath
    if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
    $bitmap.Save([IO.Path]::GetFullPath($ScreenshotPath), [System.Drawing.Imaging.ImageFormat]::Png)
} finally { $graphics.Dispose(); $bitmap.Dispose() }
Write-Output "Campus service browser action=$Action; title=$($browser.MainWindowTitle); capture=$([IO.Path]::GetFullPath($ScreenshotPath)); size=$($width)x$($height)"
