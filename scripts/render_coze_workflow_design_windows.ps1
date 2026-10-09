param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$svgPath = Join-Path $projectRoot 'coze\workflow\application_status_workflow_design.svg'
$pngPath = Join-Path $projectRoot 'coze\workflow\application_status_workflow_design.png'
$edgeCandidates = @(
    'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
)
$edgePath = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edgePath) { throw 'Microsoft Edge was not found in its Windows installation directory.' }
if (-not (Test-Path $svgPath)) { throw "Diagram source missing: $svgPath" }
$renderProfile = Join-Path ([System.IO.Path]::GetTempPath()) ('campus-workflow-render-' + [Guid]::NewGuid().ToString('N'))
$renderUri = ([System.Uri]$svgPath).AbsoluteUri
$arguments = @(
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
    '--force-device-scale-factor=1', '--window-size=1680,1040',
    "--user-data-dir=`"$renderProfile`"", "--screenshot=`"$pngPath`"", "`"$renderUri`""
)
$process = Start-Process -FilePath $edgePath -ArgumentList $arguments -PassThru
try {
    if (-not $process.WaitForExit(45000)) {
        $process.Kill()
        throw 'Diagram export timed out after 45 seconds.'
    }
    if (-not (Test-Path $pngPath)) { throw 'Edge did not produce the diagram PNG.' }
    Add-Type -AssemblyName System.Drawing
    $image = [System.Drawing.Image]::FromFile($pngPath)
    try {
        if ($image.Width -ne 1680 -or $image.Height -ne 1040) { throw 'Unexpected diagram dimensions.' }
        Write-Output "Diagram exported: $pngPath ($($image.Width)x$($image.Height))"
    } finally { $image.Dispose() }
} finally {
    if ($process.HasExited -and (Test-Path $renderProfile)) {
        Remove-Item $renderProfile -Recurse -Force -ErrorAction SilentlyContinue
    }
}
