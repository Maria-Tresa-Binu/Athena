param(
    [int]$Port = 8080,
    [switch]$InstallCloudflared
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if ($InstallCloudflared) {
    winget install --id Cloudflare.cloudflared --exact
}

 $cloudflaredCommand = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($cloudflaredCommand) {
    $cloudflared = $cloudflaredCommand.Source
} elseif (Test-Path "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe") {
    $cloudflared = "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe"
} elseif (Test-Path "$env:ProgramFiles\cloudflared\cloudflared.exe") {
    $cloudflared = "$env:ProgramFiles\cloudflared\cloudflared.exe"
} else {
    throw "cloudflared is not installed. Install it with: winget install --id Cloudflare.cloudflared --exact"
}

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}

$logPath = Join-Path $env:TEMP "athena-cloudflared-$PID.log"
$errorLogPath = Join-Path $env:TEMP "athena-cloudflared-$PID-error.log"
$serverLogPath = Join-Path $env:TEMP "athena-web-$PID.log"
$serverErrorLogPath = Join-Path $env:TEMP "athena-web-$PID-error.log"
Remove-Item -LiteralPath $logPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $errorLogPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $serverLogPath -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $serverErrorLogPath -Force -ErrorAction SilentlyContinue

$existingListener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existingListener) {
    throw "Port $Port is already in use. Stop the previous Athena process, then run this script again."
}

Write-Host "Creating the public HTTPS tunnel ..." -ForegroundColor Cyan
$tunnel = Start-Process -FilePath $cloudflared -ArgumentList "tunnel --url http://127.0.0.1:$Port --no-autoupdate" -RedirectStandardOutput $logPath -RedirectStandardError $errorLogPath -WorkingDirectory $projectRoot -PassThru

try {
    $publicUrl = $null
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        Start-Sleep -Seconds 1
        $logFiles = @($logPath, $errorLogPath) | Where-Object { Test-Path $_ }
        if ($logFiles) {
            $match = Select-String -Path $logFiles -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -First 1
            if ($match) {
                $publicUrl = [regex]::Match($match.Line, 'https://[a-z0-9-]+\.trycloudflare\.com').Value
                break
            }
        }
        if ($tunnel.HasExited) { throw "cloudflared stopped before creating a tunnel. See $logPath" }
    }
    if (-not $publicUrl) { throw "Timed out waiting for Cloudflare to create the public URL. See $logPath" }

    $env:TOOLKIT_RETURN_URL = "$publicUrl/toolkit/callback"
    Write-Host "Starting Athena on localhost:$Port ..." -ForegroundColor Cyan
    Write-Host "Toolkit OAuth callback: $env:TOOLKIT_RETURN_URL" -ForegroundColor DarkGray
    $server = Start-Process -FilePath $python -ArgumentList "-m athena.web --host 127.0.0.1 --port $Port" -WorkingDirectory $projectRoot -RedirectStandardOutput $serverLogPath -RedirectStandardError $serverErrorLogPath -PassThru

    $health = $null
    for ($attempt = 1; $attempt -le 10; $attempt++) {
        try {
            $health = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
            if ($health.StatusCode -eq 200) { break }
        } catch {
            if ($server.HasExited) { throw "Athena stopped during startup. See $serverErrorLogPath" }
            if ($attempt -eq 10) { throw "Athena did not start successfully on port $Port. See $serverErrorLogPath" }
            Start-Sleep -Seconds 1
        }
    }
    Write-Host "Open this URL from any laptop or phone: $publicUrl" -ForegroundColor Green
    Write-Host "Keep this window open while using Athena." -ForegroundColor Green
    Wait-Process -Id $tunnel.Id
}
finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
    if ($tunnel -and -not $tunnel.HasExited) {
        Stop-Process -Id $tunnel.Id -Force
    }
    Write-Host "Cloudflare logs: $logPath and $errorLogPath" -ForegroundColor DarkGray
    Write-Host "Athena logs: $serverLogPath and $serverErrorLogPath" -ForegroundColor DarkGray
}
