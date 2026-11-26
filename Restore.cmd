@echo off
chcp 65001 >nul
setlocal
set "ATLAS_PACK_DIRECTORY=%~dp0"
powershell.exe -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; try { & ([ScriptBlock]::Create([IO.File]::ReadAllText($env:ATLAS_PACK_DIRECTORY + 'Install-Pack.ps1'))) -PackDirectory $env:ATLAS_PACK_DIRECTORY -Restore; exit 0 } catch { Write-Host $_ -ForegroundColor Red; exit 1 }"
if errorlevel 1 (echo A visszaallitas nem sikerult. Zarja be az Atlast, es futtassa rendszergazdakent. / Restore failed: close Atlas and run as administrator.)
pause
