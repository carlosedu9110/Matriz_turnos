# Gestión de reemplazos — Fase 5

## Alcance

El reemplazo registra qué trabajador cubre a otro, durante qué periodo y, opcionalmente, qué tipo de
turno cubre. Las coberturas aparecen en la matriz con `↪`. Solo un usuario con rol **Admin** puede
consultar, registrar, editar, anular o reactivar reemplazos.

## Panel visual

En `/app`, el botón **Reemplazos** permite:

- Consultar reemplazos activos o anulados.
- Filtrar por periodo y ver persona ausente, reemplazante, turno y motivo.
- Registrar una cobertura nueva.
- Editar una cobertura activa.
- Anularla conservando el historial y reactivarla si ya no hay conflictos.

Las vacaciones aprobadas crean su cobertura vinculada: esas coberturas se administran desde la
solicitud de vacaciones para evitar inconsistencias.

## Reglas

- Ambas personas deben estar activas y ser distintas.
- Las fechas son inclusivas; el final no puede ser anterior al inicio y el periodo máximo es de 366 días.
- El reemplazante no puede tener otra cobertura que se solape.
- El reemplazante no puede tener un turno propio asignado durante los días en que debe cubrir.
- No se pueden modificar ni anular coberturas ligadas a vacaciones aprobadas desde este panel.
- La anulación conserva el registro. Reactivarlo vuelve a validar el estado de las personas y los conflictos.
- Las comprobaciones se hacen en el servidor; ocultar el botón a otros roles no es la medida de seguridad.

## Endpoints

| Método | Ruta | Acción |
|---|---|---|
| `GET` | `/reemplazos?activo=true&desde=AAAA-MM-DD&hasta=AAAA-MM-DD` | Consultar activos |
| `GET` | `/reemplazos?activo=false` | Consultar historial anulado |
| `POST` | `/reemplazos` | Registrar una cobertura |
| `PATCH` | `/reemplazos/{id}` | Editar participantes, fechas, turno o motivo |
| `DELETE` | `/reemplazos/{id}` | Anular sin borrar el historial |
| `POST` | `/reemplazos/{id}/reactivar` | Reactivar si supera las validaciones |

Ejemplo para crear:

```json
{
  "trabajador_ausente_id": 12,
  "trabajador_reemplazo_id": 18,
  "tipo_turno_id": 1,
  "fecha_inicio": "2026-12-10",
  "fecha_fin": "2026-12-12",
  "motivo": "Permiso"
}
```
