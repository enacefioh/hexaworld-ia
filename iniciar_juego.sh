#!/usr/bin/env bash
echo "========================================================"
echo "      Iniciando HexaWorld IA - Mundo Hexagonal"
echo "========================================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no está instalado o no se encuentra en el PATH."
    exit 1
fi

echo "[1/3] Instalando dependencias..."
pip3 install -r requirements.txt --quiet

echo ""
echo "[2/3] Conectando con LM Studio..."
echo "Host por defecto: http://localhost:1234 (o variable LM_STUDIO_HOST)"
echo ""
echo "[3/3] Iniciando servidor web en: http://127.0.0.1:8000"
echo ""

# Intentar abrir el navegador según SO
if command -v xdg-open &> /dev/null; then
    xdg-open "http://127.0.0.1:8000" &
elif command -v open &> /dev/null; then
    open "http://127.0.0.1:8000" &
fi

python3 -m uvicorn server:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
