# Vacaciones — Fase 4

## Flujo

1. El **Usuario final** abre **Vacaciones**, indica las fechas y envía la solicitud.
2. La solicitud queda **pendiente** y solo la persona y los Admin pueden verla.
3. El Admin abre la lista, revisa y:
   - **Aprueba**, opcionalmente asignando un reemplazante activo.
   - **Rechaza**, dejando una nota para la persona.
4. El usuario ve la decisión en **Mis vacaciones**. Mientras esté pendiente, puede cancelar su solicitud.
5. Las vacaciones aprobadas aparecen en la matriz como una fila verde. Si se eligió reemplazante,
   sus turnos se reflejan como cobertura; si no, los turnos quedan señalados como vacaciones sin cubrir.

## Reglas y permisos

- Solo se pueden solicitar periodos desde hoy en adelante; inicio y fin son inclusivos y el periodo
  no puede exceder un año.
- No puede haber dos solicitudes pendientes/aprobadas del mismo trabajador con fechas solapadas.
- Usuario final solo lista, solicita y cancela sus propias solicitudes pendientes.
- Solo Admin puede aprobar o rechazar solicitudes pendientes.
- Un reemplazante tiene que ser otra persona activa. Si ya tiene turno asignado en un día que tendría
  que cubrir, la aprobación se rechaza para que el Admin resuelva el conflicto.
- Las fechas aprobadas no reciben nuevas asignaciones manuales, masivas ni generadas por el ciclo.
  La operación masiva omite esos días e incluye las omisiones en el resumen.
- Rechazar requiere una nota. Una solicitud decidida no puede volver a decidirse ni cancelarse.
- Rechazo o cancelación no modifican las asignaciones. Aprobación sin reemplazante deja una alerta
  visual en la fila de vacaciones.

## Endpoints

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/vacaciones` | Admin: todas; Usuario final: propias |
| `POST` | `/vacaciones` | Usuario autenticado: solicitud propia |
| `DELETE` | `/vacaciones/{id}` | Usuario propietario: cancelar si está pendiente |
| `PATCH` | `/vacaciones/{id}` | Solo Admin: aprobar/rechazar |

Ejemplo de solicitud:

```json
{
  "fecha_inicio": "2026-12-10",
  "fecha_fin": "2026-12-20",
  "motivo": "Descanso anual"
}
```

Ejemplo de aprobación con cobertura:

```json
{
  "estado": "aprobada",
  "nota_admin": "Aprobada",
  "reemplazante_id": 12
}
```

## Esquema de datos

La tabla `vacaciones` conserva solicitante, periodo, motivo, estado (`pendiente`, `aprobada`,
`rechazada` o `cancelada`), nota administrativa y referencia opcional al reemplazo creado al aprobar.
`python -m app.db.init_db` crea la tabla si aún no existe y puede volver a ejecutarse.
