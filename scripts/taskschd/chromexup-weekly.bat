REM Run weekly on Mondays at 12:00
schtasks /create /tn "chromexup-weekly" /sc "weekly" /d "mon" /st "12:00" /tr "chromexup.exe"
