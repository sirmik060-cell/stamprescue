@echo off
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --name StampRescue --onedir --windowed --noconfirm ^
  --add-data "models;models" ^
  --collect-all pymupdf ^
  --hidden-import fitz ^
  main.py
echo.
echo Готово: dist\StampRescue\StampRescue.exe  (рядом папка models с lama.onnx)
pause