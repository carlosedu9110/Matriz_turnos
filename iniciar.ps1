# Levanta la API y el frontend sin activar el venv. Uso: .\iniciar.ps1  (luego abre http://localhost:8000/app/)
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Falta el entorno virtual. Ver README (Instalación)."; exit 1 }
& $py -m uvicorn app.main:app --port 8000
