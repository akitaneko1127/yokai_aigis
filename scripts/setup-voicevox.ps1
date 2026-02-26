# VOICEVOX Engine セットアップスクリプト
# 使い方: PowerShellで実行 → .\scripts\setup-voicevox.ps1
#
# DirectML版（GPU対応）をダウンロード・展開します。
# CPU版が必要な場合は $Variant = "cpu" に変更してください。

param(
    [string]$Variant = "directml"  # "cpu", "directml", "nvidia"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$VoicevoxDir = Join-Path $ProjectRoot "VOICEVOX"

# 既にインストール済みか確認
$RunExe = Join-Path $VoicevoxDir "run.exe"
if (Test-Path $RunExe) {
    Write-Host "[OK] VOICEVOX は既にインストール済みです: $VoicevoxDir" -ForegroundColor Green
    Write-Host "     起動: .\scripts\start-voicevox.ps1"
    exit 0
}

# GitHub APIから最新バージョンを取得
Write-Host "[1/4] 最新バージョンを確認中..." -ForegroundColor Cyan
$Release = Invoke-RestMethod -Uri "https://api.github.com/repos/VOICEVOX/voicevox_engine/releases/latest"
$Version = $Release.tag_name
Write-Host "       バージョン: $Version"

# ダウンロードURLを構築
$ArchiveName = "voicevox_engine-windows-${Variant}-${Version}.7z.001"
$DownloadUrl = "https://github.com/VOICEVOX/voicevox_engine/releases/download/${Version}/${ArchiveName}"
$DownloadPath = Join-Path $env:TEMP $ArchiveName

# NVIDIA版は2ファイルある場合がある
$ArchiveName2 = "voicevox_engine-windows-${Variant}-${Version}.7z.002"
$DownloadUrl2 = "https://github.com/VOICEVOX/voicevox_engine/releases/download/${Version}/${ArchiveName2}"
$DownloadPath2 = Join-Path $env:TEMP $ArchiveName2

Write-Host "[2/4] ダウンロード中... ($Variant版)" -ForegroundColor Cyan
Write-Host "       URL: $DownloadUrl"
Write-Host "       ファイルサイズ: 約1.7GB（しばらくお待ちください）"

# ダウンロード（プログレスバー付き）
$ProgressPreference = 'SilentlyContinue'  # 高速化
Invoke-WebRequest -Uri $DownloadUrl -OutFile $DownloadPath
Write-Host "       ダウンロード完了: $ArchiveName"

# NVIDIA版の2番目のファイル
$HasPart2 = $false
if ($Variant -eq "nvidia") {
    try {
        Invoke-WebRequest -Uri $DownloadUrl2 -OutFile $DownloadPath2
        $HasPart2 = $true
        Write-Host "       ダウンロード完了: $ArchiveName2"
    } catch {
        # 2番目のファイルがない場合は無視
    }
}

# 7-Zipで展開
Write-Host "[3/4] 展開中..." -ForegroundColor Cyan
$SevenZip = $null
$SevenZipPaths = @(
    "C:\Program Files\7-Zip\7z.exe",
    "C:\Program Files (x86)\7-Zip\7z.exe",
    (Get-Command 7z -ErrorAction SilentlyContinue).Source
)
foreach ($p in $SevenZipPaths) {
    if ($p -and (Test-Path $p)) { $SevenZip = $p; break }
}

if (-not $SevenZip) {
    Write-Host "[ERROR] 7-Zipが見つかりません。インストールしてください:" -ForegroundColor Red
    Write-Host "        https://7-zip.org/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "        またはwinget: winget install 7zip.7zip" -ForegroundColor Yellow
    exit 1
}

# 一時展開先
$TempExtract = Join-Path $env:TEMP "voicevox_extract"
if (Test-Path $TempExtract) { Remove-Item $TempExtract -Recurse -Force }

& $SevenZip x $DownloadPath "-o$TempExtract" -y | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] 展開に失敗しました" -ForegroundColor Red
    exit 1
}

# 展開されたディレクトリを特定してリネーム
$ExtractedDir = Get-ChildItem $TempExtract -Directory | Select-Object -First 1
if (-not $ExtractedDir) {
    Write-Host "[ERROR] 展開されたディレクトリが見つかりません" -ForegroundColor Red
    exit 1
}

# voicevox/ に移動
Write-Host "[4/4] 配置中..." -ForegroundColor Cyan
if (Test-Path $VoicevoxDir) { Remove-Item $VoicevoxDir -Recurse -Force }
Move-Item $ExtractedDir.FullName $VoicevoxDir

# クリーンアップ
Remove-Item $DownloadPath -Force -ErrorAction SilentlyContinue
if ($HasPart2) { Remove-Item $DownloadPath2 -Force -ErrorAction SilentlyContinue }
Remove-Item $TempExtract -Recurse -Force -ErrorAction SilentlyContinue

# 確認
if (Test-Path $RunExe) {
    Write-Host ""
    Write-Host "====================================" -ForegroundColor Green
    Write-Host " VOICEVOX セットアップ完了!" -ForegroundColor Green
    Write-Host "====================================" -ForegroundColor Green
    Write-Host ""
    Write-Host " バージョン : $Version ($Variant)" -ForegroundColor White
    Write-Host " インストール先 : $VoicevoxDir" -ForegroundColor White
    Write-Host ""
    Write-Host " 起動方法:" -ForegroundColor Yellow
    Write-Host "   .\scripts\start-voicevox.ps1" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "[ERROR] run.exe が見つかりません。展開に問題があった可能性があります。" -ForegroundColor Red
    exit 1
}
