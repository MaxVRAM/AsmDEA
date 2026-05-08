@echo off
call .venv\Scripts\activate.bat
python asmdea.py all
pnpm --dir dashboard dev
