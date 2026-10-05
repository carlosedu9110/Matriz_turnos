# Guía para cargar la información de la matriz (Fase 2)

Esta guía es para el compañero que va a registrar en el sistema los datos de la matriz de turnos:
**áreas, cargos, tipos de turno, trabajadores y reemplazos**. Puede hacerse desde Swagger
(`http://localhost:8000/docs`) o desde Postman. Solo un usuario con rol **Administrador** puede crear,
modificar o dar de baja datos; cualquier usuario autenticado puede consultarlos.

## Orden de carga (importante)

Cada paso depende del anterior:

1. **Áreas** → 2. **Cargos** (se vinculan a un área) → 3. **Tipos de turno** →
4. **Trabajadores** (se vinculan a área y cargo) → 5. **Reemplazos** (se vinculan a trabajadores y turno).

## Antes de empezar

1. La API debe estar corriendo (ver README) y la base creada con `python -m app.db.init_db`
   (la tabla `reemplazos` se crea con este mismo comando; es seguro repetirlo).
2. Inicia sesión:
   - **Swagger**: botón **Authorize** → usuario y contraseña de un Administrador.
   - **Postman**: `POST /auth/login` con `{"username": "...", "password": "..."}` y usa el
     `access_token` como *Bearer Token* en cada petición. El token dura 30 minutos.

## Paso 1 — Áreas

`POST /areas`

```json
{ "nombre": "Operaciones", "descripcion": "Operación 24/7" }
```

Guarda el `id` que responde. El nombre no puede repetirse (error `409`).

## Paso 2 — Cargos

`POST /cargos`

```json
{ "nombre": "Operador", "descripcion": "Operador de planta", "area_id": 1 }
```

## Paso 3 — Tipos de turno

`POST /tipos-turno` (horas en formato `HH:MM:SS`; un turno nocturno puede terminar "al día siguiente")

```json
{ "nombre": "Diurno",   "hora_inicio": "06:00:00", "hora_fin": "14:00:00", "color": "#F4B400" }
{ "nombre": "Tarde",    "hora_inicio": "14:00:00", "hora_fin": "22:00:00", "color": "#4285F4" }
{ "nombre": "Nocturno", "hora_inicio": "22:00:00", "hora_fin": "06:00:00", "color": "#0F9D58" }
```

(Envía cada objeto en una petición separada. Ajusta nombres y horarios a los de la matriz real.)

## Paso 4 — Trabajadores

`POST /trabajadores`

```json
{
  "documento": "1234567890",
  "nombres": "Ana María",
  "apellidos": "Pérez Gómez",
  "fecha_ingreso": "2024-03-01",
  "telefono": "3001234567",
  "area_id": 1,
  "cargo_id": 1
}
```

- `documento` es único. Si el cargo pertenece a un área distinta de `area_id`, responde `422`.
- **Opcional — dar acceso al sistema**: agrega el bloque `usuario` (rol por defecto `Trabajador`;
  usa `Administrador` solo si corresponde):

```json
"usuario": { "username": "aperez", "email": "aperez@empresa.com", "password": "ClaveSegura123!", "rol": "Trabajador" }
```

Consultar y corregir:

- `GET /trabajadores?q=Pérez` (busca por documento, nombres o apellidos) · filtros `area_id`, `cargo_id`, `activo`.
- `PATCH /trabajadores/{id}` con solo los campos a cambiar.
- `DELETE /trabajadores/{id}` es una **baja lógica** (queda inactivo y se bloquea su usuario; no se borra).

## Paso 5 — Reemplazos

`POST /reemplazos`: el trabajador `trabajador_reemplazo_id` cubre al `trabajador_ausente_id`.

```json
{
  "trabajador_ausente_id": 1,
  "trabajador_reemplazo_id": 2,
  "tipo_turno_id": 3,
  "fecha_inicio": "2026-01-10",
  "fecha_fin": "2026-01-12",
  "motivo": "Incapacidad"
}
```

Reglas que valida el sistema:

- Ambos trabajadores deben existir y estar activos, y ser personas distintas (`422`).
- `fecha_fin` no puede ser anterior a `fecha_inicio` (`422`).
- El reemplazante no puede tener otro reemplazo activo que se cruce en fechas **y** turno (`409`).

Consultar: `GET /reemplazos?trabajador_id=1&desde=2026-01-01&hasta=2026-01-31`.
Anular uno registrado por error: `DELETE /reemplazos/{id}` (baja lógica).

## Errores frecuentes

| Código | Significado | Qué hacer |
|--------|-------------|-----------|
| 401 | Sin token o token vencido | Vuelve a iniciar sesión |
| 403 | Tu usuario no es Administrador | Usa una cuenta de Administrador |
| 404 | Un id (área, cargo, trabajador, turno) no existe | Verifica el id con el `GET` correspondiente |
| 409 | Dato duplicado (nombre, documento, username, email) o reemplazo cruzado | Revisa si ya está cargado |
| 422 | Datos inválidos (fechas, cargo de otra área, campos faltantes) | Lee el campo `detail` de la respuesta |

## Lista de verificación para el compañero

- [ ] Áreas cargadas (`GET /areas`)
- [ ] Cargos cargados y ligados a su área (`GET /cargos`)
- [ ] Tipos de turno con sus horarios (`GET /tipos-turno`)
- [ ] Todos los trabajadores de la matriz (`GET /trabajadores`) sin documentos repetidos
- [ ] Reemplazos vigentes registrados (`GET /reemplazos`)

> La asignación de turnos por día (la matriz propiamente dicha) llega en la Fase 3; esta fase deja
> listos los datos maestros sobre los que se construirá.
