# Sistema de Gestión de Turnos - Matriz Turnos 24/7

## Descripción

Aplicación web para la gestión integral de turnos, vacaciones, reemplazos y horas extras en operaciones 24/7, con cumplimiento de normativa laboral colombiana.

## Características

- ✅ Matriz de turnos interactiva (vistas día/semana/mes)
- ✅ Gestión de vacaciones
- ✅ Gestión de reemplazos
- ✅ Registro y validación de horas extras
- ✅ Cálculo automático según legislación colombiana
- ✅ Roles y permisos (Administrador/Trabajador)
- ✅ Auditoría completa de cambios
- ✅ Reportes en Excel
- ✅ Integración con calendario de festivos
- ✅ Alertas de conflictos

## Stack Tecnológico

### Backend
- **Python 3.11+**
- **FastAPI**
- **SQLAlchemy**
- **MySQL**
- **JWT (PyJWT)**

### Frontend
- **HTML5**
- **CSS3**
- **JavaScript Vanilla (ES6+)**

## Estructura del Proyecto

Ver `docs/ARCHITECTURE.md` para la documentación completa de arquitectura.

## Fases de Desarrollo

1. **Fase 1**: Base del proyecto + BD + Autenticación
2. **Fase 2**: Gestión de trabajadores y reemplazos
3. **Fase 3**: Matriz de turnos
4. **Fase 4**: Vacaciones
5. **Fase 5**: Reemplazos
6. **Fase 6**: Horas extras
7. **Fase 7**: Validaciones laborales
8. **Fase 8**: Dashboards
9. **Fase 9**: Auditoría y reportes
10. **Fase 10**: Pruebas, seguridad y despliegue

## Instalación (Fase 1)

### Requisitos

- Python 3.11+
- MySQL 8+ en ejecución (o compatible), con una base de datos y usuario creados

### Pasos

```bash
# 1. Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
copy .env.example .env        # Windows
# cp .env.example .env         # Linux/Mac
# Editar .env con las credenciales de tu base de datos MySQL y SECRET_KEY

# 4. Crear el esquema de base de datos y datos base (roles + admin)
python -m app.db.init_db

# 5. Levantar el servidor de desarrollo
uvicorn app.main:app --reload
```

La API queda disponible en `http://localhost:8000` (docs interactivas en `/docs`).

Usuario administrador inicial sembrado por `init_db`: `admin` / `Admin123!` (cambiar en producción).

### Variables de entorno

Ver `.env.example` para el listado completo. Las más relevantes:

| Variable                       | Descripción                                              |
|---------------------------------|-----------------------------------------------------------|
| `DATABASE_URL`                  | URI SQLAlchemy completa (tiene prioridad sobre `DB_*`)     |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Datos de conexión MySQL individuales |
| `SECRET_KEY`                     | Clave usada para firmar los JWT (cambiar en producción)    |
| `JWT_ALGORITHM`                  | Algoritmo de firma JWT (por defecto `HS256`)               |
| `ACCESS_TOKEN_EXPIRE_MINUTES`    | Vigencia del access token                                  |
| `REFRESH_TOKEN_EXPIRE_DAYS`      | Vigencia del refresh token                                 |
| `CORS_ORIGINS`                   | Orígenes permitidos, separados por coma                    |

### Pruebas

```bash
pytest
```

Las pruebas usan una base de datos SQLite en memoria (no requieren MySQL en ejecución).

## Documentación

- `docs/ARCHITECTURE.md` - Diseño completo del sistema (Fase 1)
- `docs/DATABASE.md` - Esquema de base de datos (Fase 1)

## Licencia

Privado
