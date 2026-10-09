param(
    [ValidateSet('Navigate','Capture','Click','Keys','Text','PasteFile','Drag','Hover','Ask','NewAsk')][string]$Action = 'Capture',
    [string]$Url,
    [int]$X = 0,
    [int]$Y = 0,
    [int]$EndX = 0,
    [int]$EndY = 0,
    [string]$Value,
    [string]$ValueFile,
    [string]$ScreenshotPath = "$env:TEMP\campus-coze-current.png"
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class CampusCozeWindow {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int command);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint data, UIntPtr extra);
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort vk, scan; public uint flags, time; public UIntPtr extra; }
  [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx,dy; public uint data,flags,time; public UIntPtr extra; }
  [StructLayout(LayoutKind.Explicit)] public struct UNION { [FieldOffset(0)] public KEYBDINPUT key; [FieldOffset(0)] public MOUSEINPUT mouse; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public UNION union; }
  [DllImport("user32.dll", SetLastError=true)] static extern uint SendInput(uint n, INPUT[] input, int size);
  public static void TypeText(string value) {
    foreach (char c in value) {
      INPUT down=new INPUT(); down.type=1; down.union.key.scan=c; down.union.key.flags=4;
      INPUT up=down; up.union.key.flags=6;
      if (SendInput(2,new INPUT[]{down,up},Marshal.SizeOf(typeof(INPUT)))!=2) throw new Exception("Unicode keyboard input failed.");
    }
  }
}
'@
[void][CampusCozeWindow]::SetProcessDPIAware()
if ($Action -eq 'Navigate') {
    if ($Url -notmatch '^https://([a-z0-9-]+\.)?coze\.cn([/?]|$)') { throw 'Only an authorized Coze URL can be opened.' }
    Start-Process $Url
    Start-Sleep -Seconds 3
}
$window = [CampusCozeWindow]::GetForegroundWindow()
$windowProcessId = [uint32]0
[void][CampusCozeWindow]::GetWindowThreadProcessId($window, [ref]$windowProcessId)
$browser = Get-Process -Id $windowProcessId -ErrorAction SilentlyContinue
if (-not $browser -or $browser.ProcessName -notin @('chrome','msedge') -or $browser.MainWindowTitle -notmatch 'Coze|扣子|campus_service_status_query|campus_human_service_demo') {
    $browser = Get-Process chrome,msedge -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -match 'Coze|扣子|campus_service_status_query|campus_human_service_demo' } | Select-Object -First 1
    if (-not $browser) { throw 'No visible Coze browser window is available. No input was sent.' }
    $window = $browser.MainWindowHandle
}
if ($browser.MainWindowTitle -notmatch 'Coze|扣子|campus_service_status_query|campus_human_service_demo') { throw 'The active browser is not a Coze page. No input was sent.' }
[void][CampusCozeWindow]::ShowWindow($window, 3)
[void][CampusCozeWindow]::SetForegroundWindow($window)
Start-Sleep -Milliseconds 400
switch ($Action) {
    'Hover' { [void][CampusCozeWindow]::SetCursorPos($X,$Y) }
    'Drag' {
        [void][CampusCozeWindow]::SetCursorPos($X,$Y)
        [CampusCozeWindow]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
        Start-Sleep -Milliseconds 150
        for ($step=1; $step -le 20; $step++) {
            [void][CampusCozeWindow]::SetCursorPos(($X+($EndX-$X)*$step/20),($Y+($EndY-$Y)*$step/20))
            Start-Sleep -Milliseconds 20
        }
        [CampusCozeWindow]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
    }
    'Click' { [void][CampusCozeWindow]::SetCursorPos($X,$Y); [CampusCozeWindow]::mouse_event(2,0,0,0,[UIntPtr]::Zero); [CampusCozeWindow]::mouse_event(4,0,0,0,[UIntPtr]::Zero) }
    'Keys' { [System.Windows.Forms.SendKeys]::SendWait($Value) }
    'Text' {
        $textToType = $Value
        if ($ValueFile) { $textToType = Get-Content -LiteralPath $ValueFile -Raw -Encoding UTF8 }
        [CampusCozeWindow]::TypeText($textToType)
    }
    'PasteFile' {
        if (-not $ValueFile) { throw 'PasteFile requires ValueFile.' }
        $textToPaste = Get-Content -LiteralPath $ValueFile -Raw -Encoding UTF8
        [System.Windows.Forms.Clipboard]::SetText($textToPaste)
        [System.Windows.Forms.SendKeys]::SendWait('^v')
    }
    { $_ -in 'Ask','NewAsk' } {
        if (-not $ValueFile) { throw 'Ask requires ValueFile.' }
        if ($Action -eq 'NewAsk') {
            [void][CampusCozeWindow]::SetCursorPos(1720,1410)
            [CampusCozeWindow]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
            [CampusCozeWindow]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
            Start-Sleep -Milliseconds 800
        }
        [void][CampusCozeWindow]::SetCursorPos(2160,1410)
        [CampusCozeWindow]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
        [CampusCozeWindow]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
        $textToPaste = Get-Content -LiteralPath $ValueFile -Raw -Encoding UTF8
        [System.Windows.Forms.Clipboard]::SetText($textToPaste)
        [System.Windows.Forms.SendKeys]::SendWait('^v')
        Start-Sleep -Milliseconds 500
        [void][CampusCozeWindow]::SetCursorPos(2488,1410)
        [CampusCozeWindow]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
        [CampusCozeWindow]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
    }
}
Start-Sleep -Milliseconds 900
$bounds=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap=New-Object System.Drawing.Bitmap($bounds.Width,$bounds.Height)
$graphics=[System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.CopyFromScreen($bounds.Location,[System.Drawing.Point]::Empty,$bounds.Size)
    $bitmap.Save($ScreenshotPath,[System.Drawing.Imaging.ImageFormat]::Png)
} finally { $graphics.Dispose(); $bitmap.Dispose() }
Write-Output "Coze browser action=$Action; capture=$ScreenshotPath; size=$($bounds.Width)x$($bounds.Height)"
