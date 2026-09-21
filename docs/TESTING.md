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

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea la activación por política de ejecución, ejecuta PowerShell como usuario
normal y usa:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Después, vuelve a ejecutar:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Cuando el entorno está activo, normalmente aparece `(.venv)` al comienzo de la línea de comandos.

## 4. Instalar las dependencias

Con el entorno virtual activo:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Esto instala FastAPI, SQLAlchemy, PyMySQL, PyJWT, bcrypt, pytest y las demás dependencias del proyecto.

## 5. Ejecutar todas las pruebas

Desde la carpeta raíz del proyecto:

```bash
python -m pytest -v
```

También se puede usar directamente:

```bash
pytest -v
```

La forma `python -m pytest` es recomendable porque garantiza que se usa el pytest instalado dentro
del entorno virtual activo.

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

### Error al activar `.venv` en Windows

Ejecuta:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Luego vuelve a activar el entorno virtual.

### Error de `email-validator`

La dependencia ya está incluida en `requirements.txt`. Ejecuta:

```bash
python -m pip install -r requirements.txt
```

### Las pruebas no encuentran `app`

Verifica que el comando se está ejecutando desde la carpeta raíz, la misma donde están
`pyproject.toml`, `requirements.txt`, `app/` y `tests/`.

## 11. Desactivar el entorno virtual

Cuando termines:

```bash
deactivate
```

Para repetir las pruebas en el futuro solo necesitas volver a la carpeta del proyecto, activar
`.venv` y ejecutar `python -m pytest -v`.
