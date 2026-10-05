# Matriz de turnos (Fase 3)

Una **matriz** se identifica con un código. La primera es **`matriz_analistas`**; más adelante se
podrá crear `matriz_especialistas` (u otras) sin cambiar el código: cada matriz tiene su propio
ciclo, titulares y relevos, y el frontend las muestra en un selector.

## Cómo funciona el ciclo (4 semanas)

Hay 3 turnos (Mañana 06:00–14:00, Tarde 14:00–22:00, Noche 22:00–06:00) y **4 titulares**, cada uno en una
**fase** distinta (1 a 4) del mismo ciclo de 4 semanas. Cada semana todos avanzan una fase, así que cada día
queda exactamente un Mañana, un Tarde y un Noche, y una persona descansa.

| Semana del ciclo | Lun | Mar | Mié | Jue | Vie | Sáb | Dom |
|---|---|---|---|---|---|---|---|
| 1 | – | – | Mañana | Mañana | Mañana | Mañana | Mañana |
| 2 | Tarde | Tarde | – | Tarde | Tarde | Tarde | – |
| 3 | Mañana | Mañana | Tarde | – | Noche | Noche | Noche |
| 4 | Noche | Noche | Noche | Noche | – | – | Tarde |

Cada titular tiene un **relevo** (4 relevos en total): quien lo cubre cuando falta. Un turno nocturno
pertenece al día en que empieza.

> El horario de la mañana se tomó del Excel (06:00–14:00). Si es 07:00, se cambia en `/tipos-turno`.

## Verlo funcionando (datos demo)

```powershell
.\.venv\Scripts\python.exe -m app.db.init_db        # crea tablas y los 3 tipos de turno
.\.venv\Scripts\python.exe -m app.db.seed_matriz    # 8 personas demo + matriz_analistas + 12 semanas
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abre **http://localhost:8000/app/** e ingresa con un usuario (ej. `admin`).

- **Semana / Mes**: cada semana es un bloque (lunes a domingo) y las semanas van una debajo de otra, como en el Excel.`n- **Por turno** (color por persona) / **Por persona** (color por turno).
- Administrador: clic en un turno → **registrar ausencia** (propone al relevo) o **anular el reemplazo**.
- Administrador: **Generar turnos** aplica el ciclo a un rango de fechas (no pisa cambios manuales).
- Celda rayada = titular ausente; borde punteado con ↪ = cobertura.

## Usar los datos reales

1. Crea los 8 trabajadores (`POST /trabajadores`, ver `CARGA_MATRIZ.md`).
2. Crea la matriz (`POST /matriz/ciclos`). `fecha_ancla` debe ser un **lunes**: es el inicio de la semana 1
   para la fase 1.

```json
{
  "codigo": "matriz_analistas",
  "nombre": "Matriz de analistas",
  "fecha_ancla": "2026-01-05",
  "participantes": [
    {"trabajador_id": 1, "fase": 1, "relevo_id": 5},
    {"trabajador_id": 2, "fase": 2, "relevo_id": 6},
    {"trabajador_id": 3, "fase": 3, "relevo_id": 7},
    {"trabajador_id": 4, "fase": 4, "relevo_id": 8}
  ]
}
```

3. Genera turnos: `POST /matriz/ciclos/{id}/generar` con `{"desde": "2026-01-05", "hasta": "2026-12-27"}`.
4. Consulta: `GET /matriz?desde=2026-10-05&hasta=2026-10-11&matriz=matriz_analistas`.

Para alinear con el calendario real, elige `fecha_ancla` y las fases de modo que la semana en curso coincida
con la del Excel. Cambios puntuales: `PUT /matriz/asignaciones` (queda marcado ✎ y no se sobrescribe).

## Endpoints

| Método | Ruta | Rol |
|---|---|---|
| GET | `/matriz/ciclos` | autenticado |
| POST | `/matriz/ciclos` | Administrador |
| POST | `/matriz/ciclos/{id}/generar` | Administrador |
| GET | `/matriz?desde&hasta&matriz` | autenticado (máx. 93 días) |
| PUT | `/matriz/asignaciones` | Administrador |
| DELETE | `/matriz/asignaciones/{id}` | Administrador |

Las ausencias se registran con `/reemplazos` (Fase 2) y se reflejan automáticamente en la matriz.

## Altas y bajas de personal

Botón **Personal** (solo Administrador): lista a todas las personas y permite
**crear trabajador** (con acceso al sistema opcional), **dar / quitar acceso** (usuario y contraseña) y **dar de baja**.

**Si quien sale está en la matriz, el sistema lo advierte** y no deja la baja sin resolver:

- Muestra dónde participa (titular fase N / relevo de quién), cuántos turnos futuros tiene y cuántos reemplazos vigentes.
- Hay que **elegir a quien lo reemplaza** o **crear un trabajador nuevo** ahí mismo.
  El reemplazo hereda su puesto (fase o relevo) y sus turnos desde hoy; el historial pasado no cambia.
- Un **relevo** puede quedar sin cubrir («Dejar el puesto de relevo sin cubrir»); un **titular** no.
- Se anulan los reemplazos vigentes de la persona que sale. Sus accesos quedan bloqueados.
- Protecciones: no puedes darte de baja ni quitarte el acceso a ti mismo, ni dejar al sistema sin Administrador activo.
- Si algún titular o relevo de la matriz estuviera dado de baja (p. ej. cambios directos en la base), aparece un aviso naranja en la matriz.

API: `GET /trabajadores/{id}/impacto`, `DELETE /trabajadores/{id}?reemplazo_id=N` (o `?sin_relevo=true`),
`POST /trabajadores/{id}/usuario`, `DELETE /trabajadores/{id}/usuario`. Sin reemplazo, la baja de alguien en la matriz
responde `409` con `codigo: EN_MATRIZ`. `PATCH` ya no permite `activo=false`: la baja siempre pasa por `DELETE`.
