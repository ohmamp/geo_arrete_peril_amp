REM Create a folder named "batch-logs"
mkdir "batch-logs" 2>nul

REM Generate a timestamp
set TIMESTAMP=%DATE:/=-%_%TIME::=-%
set TIMESTAMP=%TIMESTAMP:.=-%

REM Set the log file path with timestamp
set LOGFILE="batch-logs\progress-%TIMESTAMP%.log"
set LOGFILE2="batch-logs\progress-%TIMESTAMP%.log"

REM Write task start entry to log
echo "Task started" > %LOGFILE%

REM Execute your commands
wsl -e bash -ic "conda activate geo-arretes; cd /mnt/c/Users/Anthony/Documents/Github/geo-arretes/; scripts/process.sh;" >> %LOGFILE% 2>&1

REM Write task completion entry to log
echo "Task completed" >> %LOGFILE%

copy %LOGFILE% %LOGFILE2%

timeout 5 > NUL