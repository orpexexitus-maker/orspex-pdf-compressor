@echo off
REM ORSPEX PDF Compressor — build script
pyinstaller --onefile --windowed ^
  --name "ORSPEX PDF Compressor" ^
  --icon "assets\orspex.ico" ^
  --add-data "assets\orspex.ico;assets" ^
  --add-data "assets\orspex.png;assets" ^
  pdf_compressor.py
echo.
echo Built: dist\ORSPEX PDF Compressor.exe
pause