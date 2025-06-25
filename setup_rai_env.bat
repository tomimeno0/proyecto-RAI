@echo off
echo 🚧 Eliminando entornos virtuales antiguos...

REM Borra el entorno viejo del escritorio (si existe)
IF EXIST "C:\Users\tomim\Desktop\RAI\.venv" (
    rmdir /s /q "C:\Users\tomim\Desktop\RAI\.venv"
    echo ✅ Eliminado: C:\Users\tomim\Desktop\RAI\.venv
)

REM Borra el entorno actual del proyecto (si existe)
IF EXIST ".venv" (
    rmdir /s /q ".venv"
    echo ✅ Eliminado: .venv actual
)

echo 🔄 Creando nuevo entorno virtual...
python -m venv .venv

echo ✅ Entorno creado. Activando...
call .venv\Scripts\activate.bat

echo 📦 Instalando dependencias necesarias...
pip install --upgrade pip
pip install pipwin
pipwin install pyaudio
pip install flask requests keyboard SpeechRecognition inputimeout

echo 🧾 Guardando requirements.txt...
pip freeze > requirements.txt

echo ✅ Listo. RAI tiene un entorno limpio y funcional.
pause
