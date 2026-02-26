# VOICEVOX Engine 起動スクリプト
# 使い方: .\scripts\start-voicevox.ps1
#
# 以下の順でVOICEVOXを探します:
#   1. D:\youkaigis\VOICEVOX\run.exe       (エンジン単体版)
#   2. D:\youkaigis\VOICEVOX\vv-engine\run.exe (エディタ版のエンジン)
#   3. 既にport 50021で起動済みならそのまま使用

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# 既に起動しているか確認
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:50021/version" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] VOICEVOX Engine は既に起動しています (port 50021)" -ForegroundColor Green
    Write-Host "     バージョン: $($resp.Content)" -ForegroundColor White
    exit 0
} catch {
    # 未起動 → 起動する
}

# run.exe を探す
$Candidates = @(
    (Join-Path $ProjectRoot "VOICEVOX" "run.exe"),
    (Join-Path $ProjectRoot "VOICEVOX" "vv-engine" "run.exe"),
    (Join-Path $ProjectRoot "VOICEVOX" "VOICEVOX" "vv-engine" "run.exe")
)

$RunExe = $null
foreach ($path in $Candidates) {
    if (Test-Path $path) {
        $RunExe = $path
        break
    }
}

if (-not $RunExe) {
    Write-Host "[ERROR] VOICEVOXが見つかりません。" -ForegroundColor Red
    Write-Host ""
    Write-Host "  以下のいずれかの方法で配置してください:" -ForegroundColor Yellow
    Write-Host "    A) エンジン版: D:\youkaigis\VOICEVOX\run.exe" -ForegroundColor White
    Write-Host "    B) エディタ版: D:\youkaigis\VOICEVOX\ にインストール" -ForegroundColor White
    Write-Host "    C) セットアップスクリプト: .\scripts\setup-voicevox.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "  または、VOICEVOXアプリを別途起動してもOKです。" -ForegroundColor Gray
    exit 1
}

Write-Host "VOICEVOX Engine 起動中..." -ForegroundColor Cyan
Write-Host "  実行ファイル: $RunExe" -ForegroundColor White
Write-Host "  API: http://localhost:50021" -ForegroundColor White
Write-Host "  Docs: http://localhost:50021/docs" -ForegroundColor White
Write-Host "  停止: Ctrl+C" -ForegroundColor Gray
Write-Host ""

& $RunExe --host 127.0.0.1 --port 50021
