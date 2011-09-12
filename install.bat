@echo off

setlocal
for %%a in (python.exe) do set python_path=%%~dp$PATH:a
echo Installing to %python_path%

if not exist %python_path%\Lib\site-packages\xpd      mkdir %python_path%\Lib\site-packages\xpd
if not exist %python_path%\Lib\site-packages\Scripts  mkdir %python_path%\Lib\site-packages\Scripts

xcopy /F/Y scripts\xpd %python_path%\Scripts\xpd
xcopy /F/Y xpd\*.py %python_path%\Lib\site-packages\xpd\
