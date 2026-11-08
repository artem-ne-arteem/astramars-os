# AstraMars OS installer bootstrap (ASCII only, safe for "irm | iex").
# Usage (PowerShell):  irm https://artem-ne-arteem.github.io/astramars-os/install.ps1 | iex
# Downloads setup.ps1 (UTF-8), saves it with BOM and runs it as administrator.
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$url = "https://artem-ne-arteem.github.io/astramars-os/setup.ps1"
$dst = Join-Path $env:TEMP "AstraMars-Setup.ps1"
$bytes = (New-Object Net.WebClient).DownloadData($url)
$text = [Text.Encoding]::UTF8.GetString($bytes).TrimStart([char]0xFEFF)
[IO.File]::WriteAllText($dst, $text, (New-Object Text.UTF8Encoding $true))
Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$dst`""
