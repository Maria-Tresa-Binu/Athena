param(
    [Parameter(Mandatory = $true)]
    [string]$ReturnUrl,
    [ValidateSet("gmail", "google-calendar")]
    [string]$Connector = "gmail",
    [string]$UserId = "athena-user"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolkitRoot = Join-Path $projectRoot "mcp_servers\toolkit"
Set-Location $toolkitRoot

node scripts\authorize.mjs --connector $Connector --user-id $UserId --return-url $ReturnUrl
