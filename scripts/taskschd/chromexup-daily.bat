REM Run daily at 12:00
schtasks /create /tn "chromexup-daily" /sc "daily" /st "12:00" /tr "chromexup.exe"
