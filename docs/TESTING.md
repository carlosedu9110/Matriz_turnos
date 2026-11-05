# Guía paso a paso para ejecutar las pruebas

Esta guía explica cómo preparar el proyecto y ejecutar las pruebas automatizadas de la Fase 1.
Las pruebas usan una base de datos SQLite temporal en memoria, por lo que **no es necesario tener
MySQL encendido** para ejecutarlas.

## 1. Requisitos

- Python 3.11 o superior.
- Git, si se va a descargar el proyecto desde GitHub.
- Una terminal:
  - Windows: PowerShell.
  - Linux/macOS: Terminal.

## 2. Descargar el proyecto

Desde una terminal, ejecuta:

```bash
git clone https://github.com/carlosedu9110/Matriz_turnos.git
cd Matriz_turnos
```

Si las pruebas están en una rama o pull request que todavía no está en `main`, cambia a esa rama:

```bash
git fetch origin
git checkout carlosedu9110-fase1-base-bd-auth
```

## 3. Crear un entorno virtual

El entorno virtual mantiene las dependencias del proyecto separadas de las de tu computador.
**No es necesario activarlo**: basta con llamar al Python del entorno por su ruta. Así se evita el
error de `Activate.ps1` cuando una política de grupo (Group Policy) bloquea la ejecución de scripts
en PowerShell (no cambies la política del sistema).

### Windows PowerShell

```powershell
python -m venv .venv
```

### Linux/macOS

```bash
python3 -m venv .venv
```

## 4. Instalar las dependencias

Ejecuta siempre los comandos desde la carpeta raíz del proyecto (donde está `pyproject.toml`).

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Linux/macOS:

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Esto instala FastAPI, SQLAlchemy, PyMySQL, PyJWT, bcrypt, pytest y las demás dependencias del proyecto.

## 5. Ejecutar todas las pruebas

Comando soportado, desde la carpeta raíz del proyecto:

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Linux/macOS:

```bash
.venv/bin/python -m pytest -v
```

Para un archivo concreto: `.\.venv\Scripts\python.exe -m pytest tests\test_models.py -v`.

> **No ejecutes los archivos de `tests/` con "Run Python File" ni con `python tests\test_models.py`.**
> Los tests son módulos de pytest, no scripts: ejecutados así, Python solo añade la carpeta `tests/`
> al path y falla con `ModuleNotFoundError: No module named 'app'`. La configuración
> (`pythonpath = ["."]` en `pyproject.toml`) solo aplica cuando se lanza con pytest.

### Usar VS Code

1. `Ctrl+Shift+P` → **Python: Select Interpreter** → elige `.venv\Scripts\python.exe`.
2. Abre el panel **Testing** (icono del matraz) → **Configure Python Tests** → **pytest** → carpeta `tests`.
3. Ejecuta las pruebas desde el panel Testing (botón ▶), no con el botón "Run Python File".

### Opcional: activar el entorno

Solo si tu equipo lo permite (en Linux/macOS: `source .venv/bin/activate`; en Windows:
`.\.venv\Scripts\Activate.ps1`). Entonces puedes usar `python -m pytest -v` directamente.
## 6. Resultado esperado

La salida debe terminar de forma similar a:

```text
============================= test session starts =============================
collected 12 items
...
======================= 12 passed, 2 warnings in 2.09s ========================
```

Los warnings de compatibilidad de `httpx`/`Starlette` no hacen fallar las pruebas. El resultado
importante es que todos los tests indiquen `PASSED` y que el resumen muestre `12 passed`.

## 7. Qué se está probando

### Autenticación (`tests/test_auth.py`)

- Login exitoso con usuario y contraseña correctos.
- Rechazo de contraseña incorrecta.
- Rechazo de usuario inexistente.
- Rechazo de `/auth/me` sin token.
- Acceso correcto a `/auth/me` con un JWT válido.
- Rechazo de un JWT inválido.

### Modelo de datos (`tests/test_models.py`)

- Relaciones entre área, cargo y trabajador.
- Documento de trabajador único.
- Username y email de usuario únicos.
- Relación de muchos a muchos entre usuarios y roles.
- Creación de tipos de turno.

### Servicio (`tests/test_health.py`)

- Respuesta correcta de `GET /health`.

## 8. Ejecutar una prueba o grupo específico

Ejecutar solo autenticación:

```bash
python -m pytest tests/test_auth.py -v
```

Ejecutar solo modelos:

```bash
python -m pytest tests/test_models.py -v
```

Ejecutar un test por su nombre:

```bash
python -m pytest tests/test_auth.py::test_login_success -v
```

## 9. Ejecutar pruebas con cobertura

Para generar un informe de cobertura:

```bash
python -m pytest --cov=app --cov-report=term-missing
```

Para generar también un informe HTML:

```bash
python -m pytest --cov=app --cov-report=html
```

Después abre `htmlcov/index.html` en un navegador.

## 10. Problemas frecuentes

### `python` no se reconoce

Instala Python 3.11 o superior y marca la opción **Add Python to PATH** durante la instalación.
En Linux/macOS, prueba `python3` en lugar de `python`.

### `No module named pytest`

Activa el entorno virtual y reinstala:

```bash
python -m pip install -r requirements.txt
```

### Error al activar `.venv` en Windows (PermissionDenied / ExecutionPolicyOverride)

Una política de grupo puede impedir `Activate.ps1` y `Set-ExecutionPolicy`. No hace falta activar: usa
`.\.venv\Scripts\python.exe -m pytest -v`. No modifiques la política del sistema.

### `ModuleNotFoundError: No module named 'app'`

Ocurre al ejecutar un archivo de `tests/` como script ("Run Python File"). Usa `python -m pytest` desde la raíz.

### Error de `email-validator`

La dependencia ya está incluida en `requirements.txt`. Ejecuta:

```bash
python -m pip install -r requirements.txt
```

### Las pruebas no encuentran `app`

Verifica que el comando se está ejecutando desde la carpeta raíz, la misma donde están
`pyproject.toml`, `requirements.txt`, `app/` y `tests/`.

## 11. Al terminar

Si activaste el entorno virtual, ejecuta `deactivate`. Para repetir las pruebas basta volver a la raíz y ejecutar
`.\.venv\Scripts\python.exe -m pytest -v`.
