@echo off
rem ETL terjadwal ke database cloud, dipanggil Windows Task Scheduler.
rem Pemakaian: scripts\etl_terjadwal.cmd [path\ke\python.exe]
rem Membaca DATABASE_URL dari .env.neon dan menambahkan log ke logs\etl.log.
setlocal
cd /d "%~dp0.."

set "PYTHON_EXE=python"
if not "%~1"=="" set "PYTHON_EXE=%~1"
if not exist logs mkdir logs
set "PYTHONPATH=src"

echo ==== %date% %time% ==== >> logs\etl.log
"%PYTHON_EXE%" -m idx_pipeline.main --env-file .env.neon >> logs\etl.log 2>&1
set "KODE=%ERRORLEVEL%"
echo ==== selesai, kode keluar %KODE% ==== >> logs\etl.log
exit /b %KODE%
