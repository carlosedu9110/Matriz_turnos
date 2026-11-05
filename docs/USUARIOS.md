# Usuarios, roles, cargos y permisos

## Dos conceptos independientes

| Rol (permiso del sistema) | Cargo (posición laboral) |
|---|---|
| `Admin` | `Analista` |
| `Usuario final` | `Especialista` |
|  | `Admin` |

Un usuario puede tener, por ejemplo, **rol `Usuario final` y cargo `Analista`**, o **rol `Admin` y cargo
`Especialista`**. Los permisos siempre se calculan a partir del **rol**, nunca del cargo.
Cada cuenta tiene exactamente un rol.
El modelo `Trabajador` conserva los datos laborales; `Usuario` contiene el correo, hash de contraseña
y roles de acceso.

## Permisos

- **Admin:** administra cuentas, perfil y cargos; asigna, edita y elimina turnos; gestiona reemplazos,
  catálogos y ciclos.
- **Usuario final:** consulta su perfil, su matriz y únicamente las asignaciones en las que participa.
- Estas reglas se aplican en las dependencias de FastAPI. Ocultar botones en el frontend no sustituye
  la autorización del servidor: llamadas directas sin token reciben `401` y llamadas con rol incorrecto
  reciben `403`.
- Cargo `Admin` no da permisos administrativos. Solo el rol `Admin` autoriza las operaciones.

## Crear y editar usuarios

Solo un Admin puede usar el panel **Usuarios** o los endpoints `/usuarios`:

- `POST /usuarios`: nombres, apellidos, correo, teléfono, cargo y rol.
- `PATCH /usuarios/{id}`: modifica esos datos; correo duplicado da `409` y cargo/rol se validan.
- `POST /usuarios/{id}/desactivar` / `POST /usuarios/{id}/activar`: controla el acceso sin borrar
  al trabajador ni su historial. Si está en la matriz, se pide un reemplazo antes de desactivarlo.
- `POST /usuarios/{id}/reenviar-invitacion`: vuelve a enviar el enlace para crear una contraseña.

El Admin **no establece ni recibe la contraseña**. Al crear la cuenta, el servidor genera una clave
aleatoria no conocida y envía al usuario un enlace temporal para que cree su contraseña. Para
trabajadores ya registrados sin cuenta, **Usuarios → Dar acceso a trabajador** vincula un correo y
un rol al registro existente.

## Correo y recuperación de acceso

- El correo es obligatorio, se valida con formato de email, se normaliza a minúsculas y es único.
- El login acepta el correo o el identificador de usuario.
- `POST /auth/forgot-password` recibe `{ "email": "persona@empresa.com" }`. Siempre devuelve el mismo
  mensaje, exista o no la cuenta, para no revelar qué correos están registrados.
- `POST /auth/reset-password` recibe el token y la nueva contraseña (mínimo 8 caracteres). El token
  caduca y solo se puede usar una vez; cambiar la contraseña invalida enlaces anteriores.
- Las cuentas desactivadas no pueden iniciar sesión ni solicitar recuperación de contraseña.

### Configurar envío de correo

En desarrollo, `EMAIL_BACKEND=console` imprime el enlace en la consola del servidor y no envía correo
real. En producción, configurar el proveedor SMTP en `.env`:

```dotenv
FRONTEND_BASE_URL=https://tu-dominio
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.tu-proveedor.com
SMTP_PORT=587
SMTP_USER=usuario-smtp
SMTP_PASSWORD=clave-de-aplicacion
SMTP_FROM=no-reply@tu-dominio
SMTP_STARTTLS=true
RESET_TOKEN_EXPIRE_MINUTES=60
INVITE_TOKEN_EXPIRE_HOURS=72
```

No guardar credenciales SMTP en Git ni compartirlas en capturas. Si el proveedor no está configurado
o falla, la cuenta se crea sin mostrar contraseña y la respuesta indica que el correo no pudo enviarse;
el Admin puede reenviar la invitación después de corregir la configuración.

## Asignaciones

La matriz de ciclos sirve como programación automática. Para una asignación puntual, el Admin puede
activar **Asignar turnos** en la interfaz o usar:

- `GET /matriz/asignaciones?desde=AAAA-MM-DD&hasta=AAAA-MM-DD` para consultar la persona, fecha y turno.
- `PUT /matriz/asignaciones` para crear una asignación.
- `PATCH /matriz/asignaciones/{id}` para modificar usuario, turno o fecha.
- `DELETE /matriz/asignaciones/{id}` para eliminarla.

En estas operaciones manuales solo se seleccionan cuentas activas. La API rechaza personal inactivo
o un trabajador que no tenga cuenta de usuario. La generación cíclica conserva los registros
anteriores; omite trabajadores desactivados y no sobrescribe turnos manuales.

## Migración desde roles anteriores

Al ejecutar `python -m app.db.init_db`, el sistema migra `Administrador` → `Admin` y
`Trabajador` → `Usuario final`, consolida cada cuenta a un solo rol, elimina roles legados ajenos a
los dos permitidos y crea/reactiva los cargos `Analista`, `Especialista` y `Admin`. La operación es idempotente.
