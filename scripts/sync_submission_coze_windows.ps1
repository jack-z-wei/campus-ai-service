$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $Root "submission"
$CozeSource = Join-Path $Root "coze"
$CozeTarget = Join-Path $Out "01_Coze_Version\coze"

if (-not (Test-Path (Join-Path $Out "package_manifest.json"))) {
    throw "The prepared submission package is missing package_manifest.json."
}
if (-not (Test-Path $CozeSource)) {
    throw "The current Coze evidence folder is missing."
}

# Replace only the packaged Coze snapshot; the canonical project evidence remains untouched.
if (Test-Path $CozeTarget) {
    Remove-Item $CozeTarget -Recurse -Force
}
New-Item -ItemType Directory -Path $CozeTarget -Force | Out-Null
Copy-Item -Path (Join-Path $CozeSource "*") -Destination $CozeTarget -Recurse -Force
Copy-Item (Join-Path $Root "reports\Coze_Python_Engineering_Mapping.md") `
    (Join-Path $Out "01_Coze_Version\module_mapping.md") -Force

$ScreenshotPngCount = @(Get-ChildItem (Join-Path $CozeTarget "screenshots") -Filter "*.png" -File).Count
$ScreenshotNote = "Coze platform screenshots: $ScreenshotPngCount PNG files. See screenshots index in coze/截图清单.md." + [Environment]::NewLine + `
    "Run outputs and declared limits: results.csv, experiment_sheet.csv, retrieval_parameter_comparison.csv, and logs/agent-evaluation-20261007.md." + [Environment]::NewLine + `
    "Agent remains an unpublished draft; billing and hidden per-turn tool traces are not claimed as verified."
Set-Content -Path (Join-Path $CozeTarget "screenshots\README.txt") -Value $ScreenshotNote -Encoding UTF8

$EvalReportNames = @(
    "PROGRESS.md",
    "HUMAN_TODO.md",
    "FINAL_AUDIT.md",
    "EXTERNAL_DEPENDENCIES.md",
    "Agent_Baseline.md",
    "Agent_Evaluation.md",
    "Optimization_Comparison.md",
    "Prompt_Comparison.md",
    "RAG_Baseline.md",
    "Failure_Analysis.md",
    "评分表_V1_V2.csv",
    "评分说明.md",
    "three_track_comparison.csv",
    "Coze_Python_Engineering_Mapping.md"
)
$EvalTarget = Join-Path $Out "04_Evaluation\reports"
foreach ($Name in $EvalReportNames) {
    $Source = Join-Path $Root "reports\$Name"
    if (Test-Path $Source) {
        Copy-Item $Source (Join-Path $EvalTarget $Name) -Force
    }
}
Copy-Item (Join-Path $Root "evaluation\failure_cases.json") `
    (Join-Path $Out "04_Evaluation\evaluation\failure_cases.json") -Force

# Refresh task records in both packaged views from the project source of truth.
foreach ($RelativeTarget in @("04_Evaluation\TASK", "03_AI_Coding_Version\TASK")) {
    $Target = Join-Path $Out $RelativeTarget
    if (Test-Path $Target) {
        Remove-Item $Target -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
    Copy-Item -Path (Join-Path $Root "TASK\*") -Destination $Target -Recurse -Force
}

foreach ($Name in @("final_report.md", "FINAL_AUDIT.md", "报告待填写项.md", "Failure_Analysis.md", "requirements_matrix.md", "Agent_Evaluation.md", "optimization_quality_metrics.svg")) {
    Copy-Item (Join-Path $Root "reports\$Name") `
        (Join-Path $Out "05_Final_Report\$Name") -Force
}
$DemoNote = "campus_ui_home.png is a real screenshot captured from the Windows local page; it does not claim that the submitter personally completed a live demo. Do not include API keys or personal information."
Set-Content -Path (Join-Path $Out "06_Demo\screenshots\README.txt") -Value $DemoNote -Encoding UTF8
$ReportPath = Join-Path $Out "05_Final_Report\final_report.md"
$Report = Get-Content $ReportPath -Raw -Encoding UTF8
$Report = $Report.Replace("../docs/campus/source_manifest.json", "../02_Python_Version/docs/campus/source_manifest.json")
$Report = $Report.Replace("../coze/source_manifest.csv", "../01_Coze_Version/coze/source_manifest.csv")
$Report = $Report.Replace("../coze/screenshots/", "../01_Coze_Version/coze/screenshots/")
$Report = $Report.Replace("../coze/workflow/", "../01_Coze_Version/coze/workflow/")
$Report = $Report.Replace('[three_track_comparison.csv](three_track_comparison.csv)', '[three_track_comparison.csv](../04_Evaluation/reports/three_track_comparison.csv)')
$Report = $Report.Replace('](评分表_V1_V2.csv)', '](../04_Evaluation/reports/评分表_V1_V2.csv)')
Set-Content $ReportPath $Report -Encoding UTF8

Write-Output "Synchronized $ScreenshotPngCount Coze screenshots and the latest report evidence."
Write-Output "Next, run scripts/build_submission_package_windows.py --refresh-manifest with Windows Python."
