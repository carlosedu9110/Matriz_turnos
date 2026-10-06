# Arquitectura del sistema — Fase 1

## Visión general

El backend está construido con **FastAPI** siguiendo una arquitectura por capas, separando
responsabilidades para facilitar el crecimiento del proyecto en las fases posteriores.

```
app/
├── main.py              # Punto de entrada: crea la app FastAPI, monta middlewares y routers
├── config.py            # Configuración (pydantic-settings) leída desde variables de entorno / .env
├── db/
│   ├── session.py       # Engine, SessionLocal, Base declarativa y dependencia get_db
│   └── init_db.py       # Script para crear el esquema y sembrar datos base (roles, admin)
├── models/               # Modelos ORM (SQLAlchemy) — una entidad por archivo
│   ├── area.py
│   ├── cargo.py
│   ├── rol.py
│   ├── usuario_rol.py   # Tabla de asociación N:M Usuario-Rol
│   ├── tipo_turno.py
│   ├── trabajador.py
│   └── usuario.py
├── schemas/              # Esquemas Pydantic (request/response) — DTOs, no exponen el ORM directamente
│   ├── auth.py
│   └── usuario.py
├── core/
│   ├── security.py       # Hashing de contraseñas (bcrypt) y emisión/validación de JWT
│   └── dependencies.py   # Dependencias FastAPI: usuario autenticado, control de roles
├── services/
│   └── auth_service.py   # Lógica de negocio de autenticación (independiente de HTTP)
└── api/routers/
    ├── health.py          # GET /health
    └── auth.py            # POST /auth/login, GET /auth/me
```

## Capas y responsabilidades

- **`api/routers`**: capa HTTP. Traduce requests/responses, delega la lógica a `services`.
- **`services`**: lógica de negocio pura (recibe una `Session` de SQLAlchemy), reutilizable y testeable
  sin depender de FastAPI.
- **`models`**: entidades ORM y sus relaciones/restricciones.
- **`schemas`**: contratos de entrada/salida de la API (Pydantic), desacoplados del modelo de datos.
- **`core`**: utilidades transversales (seguridad, dependencias de autorización).
- **`db`**: configuración de conexión y utilidades de inicialización de esquema.

## Autenticación y autorización

- Login por `username` + `password` (`POST /auth/login`), devuelve un **access token** (corta duración)
  y un **refresh token** (larga duración), ambos JWT firmados con `SECRET_KEY` (HS256).
- Las contraseñas se almacenan con hash **bcrypt** (vía `passlib`), nunca en texto plano.
- `GET /auth/me` requiere un access token válido (`Authorization: Bearer <token>`) y devuelve el usuario
  autenticado junto con sus roles.
- El control de acceso por rol se implementa con la dependencia `require_roles("Administrador")`,
  reutilizable en cualquier endpoint de fases futuras.

## Modelo de dominio (Fase 1)

Ver `docs/DATABASE.md` para el detalle de entidades, relaciones y restricciones.

## Decisiones de diseño

- **Trabajador vs. Usuario**: se separan intencionalmente. `Trabajador` modela la información laboral/
  personal (documento, nombres, área, cargo), mientras que `Usuario` modela únicamente las credenciales
  de acceso al sistema (username, email, password). Un `Trabajador` puede existir sin tener acceso al
  sistema (relación 1:1 opcional desde `Trabajador`, obligatoria desde `Usuario`).
- **Roles N:M**: un usuario puede tener más de un rol (tabla de asociación `usuario_rol`), aunque en
  Fase 1 solo se usan `Administrador` y `Trabajador`.
- **JWT sin estado en servidor**: no se persisten tokens; la revocación/rotación de refresh tokens queda
  fuera del alcance de la Fase 1.
- **SQLAlchemy 2.0 style** (`Mapped[...]`, `mapped_column`) para tipado explícito de modelos.
- **Alembic** se deja configurado (`alembic/`) para migraciones incrementales en fases futuras; en Fase 1
  también se provee `app/db/init_db.py` como alternativa rápida de bootstrap (crea tablas + siembra roles
  y un usuario administrador inicial).
