"""Servicio de trabajadores: validaciones, accesos (usuarios) y bajas con impacto en la matriz."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.roles import CARGOS, ROL_ADMIN
from app.models import Area, Asignacion, Cargo, CicloParticipante, CicloTurno, Reemplazo, Rol, Trabajador, Usuario
from app.schemas.trabajador import ImpactoOut, PosicionMatriz, TrabajadorCreate, UsuarioCreate
from app.services.acceso_service import (
    crear_usuario_con_invitacion,
    email_en_uso,
    enviar_invitacion,
    obtener_rol,
)
from app.services.common import commit_or_409, get_or_404


def validar_area_cargo(db: Session, area_id: int | None, cargo_id: int | None) -> None:
    area = get_or_404(db, Area, area_id, "Área") if area_id is not None else None
    cargo = get_or_404(db, Cargo, cargo_id, "Cargo") if cargo_id is not None else None
    if cargo and cargo.nombre not in CARGOS:
        raise HTTPException(422, "Cargo no disponible. Usa Analista, Especialista o Admin")
    if area and cargo and cargo.area_id is not None and cargo.area_id != area.id:
        raise HTTPException(422, "El cargo no pertenece al área indicada")


def crear_trabajador(db: Session, datos: TrabajadorCreate) -> Trabajador:
    validar_area_cargo(db, datos.area_id, datos.cargo_id)
    cargo_usuario = None
    if datos.usuario is not None:
        if datos.usuario.cargo is None:
            raise HTTPException(422, "El cargo es obligatorio para crear una cuenta de usuario")
        if email_en_uso(db, datos.usuario.email):
            raise HTTPException(409, "Ya existe un usuario con ese correo")
        obtener_rol(db, datos.usuario.rol)
        cargo_usuario = db.query(Cargo).filter(
            Cargo.nombre == datos.usuario.cargo, Cargo.activo.is_(True)
        ).first()
        if cargo_usuario is None:
            raise HTTPException(422, f"El cargo '{datos.usuario.cargo}' no está disponible")
        if datos.area_id is not None and cargo_usuario.area_id not in (None, datos.area_id):
            raise HTTPException(422, "El cargo no pertenece al área indicada")
        if datos.cargo_id is not None and cargo_usuario.id != datos.cargo_id:
            raise HTTPException(422, "El cargo del trabajador y el de su cuenta deben coincidir")

    trabajador = Trabajador(**datos.model_dump(exclude={"usuario"}))
    if cargo_usuario is not None and trabajador.cargo is None:
        trabajador.cargo = cargo_usuario
    db.add(trabajador)
    usuario = None
    if datos.usuario is not None:
        usuario = crear_usuario_con_invitacion(db, trabajador, datos.usuario.email, datos.usuario.rol)
    commit_or_409(db, "Documento o correo ya registrados")
    db.refresh(trabajador)
    if usuario is not None:
        enviar_invitacion(usuario)
    return trabajador


# ---- Accesos (usuarios) ----
def es_ultimo_admin(db: Session, usuario: Usuario) -> bool:
    if not usuario.activo or ROL_ADMIN not in {r.nombre for r in usuario.roles}:
        return False
    activos = (
        db.query(Usuario).join(Usuario.roles).filter(Rol.nombre == ROL_ADMIN, Usuario.activo.is_(True)).count()
    )
    return activos <= 1


def dar_acceso(db: Session, trabajador: Trabajador, datos: UsuarioCreate) -> tuple[Usuario, bool]:
    """Crea la cuenta y envía la invitación; el Admin nunca define ni conoce la contraseña."""
    if trabajador.usuario is not None:
        raise HTTPException(409, "El trabajador ya tiene acceso al sistema")
    if not trabajador.activo:
        raise HTTPException(422, "El trabajador está dado de baja")
    if datos.cargo is None:
        raise HTTPException(422, "El cargo es obligatorio para crear una cuenta de usuario")
    if email_en_uso(db, datos.email):
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    obtener_rol(db, datos.rol)
    cargo = db.query(Cargo).filter(Cargo.nombre == datos.cargo).first()
    if cargo is None or not cargo.activo:
        raise HTTPException(422, f"El cargo '{datos.cargo}' no está disponible")
    trabajador.cargo = cargo
    usuario = crear_usuario_con_invitacion(db, trabajador, datos.email, datos.rol)
    commit_or_409(db, "Correo ya registrado")
    db.refresh(usuario)
    return usuario, enviar_invitacion(usuario)


def quitar_acceso(db: Session, trabajador: Trabajador, actor: Usuario) -> None:
    """Compatibilidad de la ruta antigua: ahora desactiva la cuenta, no la elimina."""
    usuario = trabajador.usuario
    if usuario is None:
        raise HTTPException(404, "El trabajador no tiene acceso al sistema")
    dar_de_baja(db, trabajador, actor)


# ---- Bajas ----
def _participaciones(db: Session, trabajador_id: int) -> list[CicloParticipante]:
    return (
        db.query(CicloParticipante)
        .join(CicloTurno, CicloTurno.id == CicloParticipante.ciclo_id)
        .filter(
            CicloTurno.activo.is_(True),
            or_(CicloParticipante.trabajador_id == trabajador_id, CicloParticipante.relevo_id == trabajador_id),
        )
        .all()
    )


def _reemplazos_vigentes(db: Session, trabajador_id: int, hoy: date):
    return db.query(Reemplazo).filter(
        Reemplazo.activo.is_(True),
        Reemplazo.fecha_fin >= hoy,
        or_(Reemplazo.trabajador_ausente_id == trabajador_id, Reemplazo.trabajador_reemplazo_id == trabajador_id),
    )


def calcular_impacto(db: Session, trabajador: Trabajador) -> ImpactoOut:
    hoy = date.today()
    posiciones = []
    for p in _participaciones(db, trabajador.id):
        es_titular = p.trabajador_id == trabajador.id
        posiciones.append(
            PosicionMatriz(
                ciclo_id=p.ciclo_id,
                ciclo_codigo=p.ciclo.codigo,
                ciclo_nombre=p.ciclo.nombre,
                rol="titular" if es_titular else "relevo",
                fase=p.fase,
                titular=None if es_titular else f"{p.trabajador.nombres} {p.trabajador.apellidos}",
            )
        )
    futuras = db.query(Asignacion).filter(Asignacion.trabajador_id == trabajador.id, Asignacion.fecha >= hoy).count()
    return ImpactoOut(
        en_matriz=bool(posiciones),
        posiciones=posiciones,
        asignaciones_futuras=futuras,
        reemplazos_activos=_reemplazos_vigentes(db, trabajador.id, hoy).count(),
    )


def dar_de_baja(
    db: Session, trabajador: Trabajador, actor: Usuario, reemplazo_id: int | None = None, sin_relevo: bool = False
) -> None:
    """Baja lógica. Si está en una matriz activa exige un reemplazo (o dejar sin relevo si solo es relevo)."""
    if not trabajador.activo:
        raise HTTPException(409, "El trabajador ya está dado de baja")
    usuario = trabajador.usuario
    if usuario is not None:
        if usuario.id == actor.id:
            raise HTTPException(409, "No puedes darte de baja a ti mismo")
        if es_ultimo_admin(db, usuario):
            raise HTTPException(409, "No se puede dar de baja al único Admin activo")

    hoy = date.today()
    partic = _participaciones(db, trabajador.id)
    es_titular = any(p.trabajador_id == trabajador.id for p in partic)

    if partic and reemplazo_id is None and (es_titular or not sin_relevo):
        impacto = calcular_impacto(db, trabajador)
        raise HTTPException(
            409,
            detail={
                "codigo": "EN_MATRIZ",
                "mensaje": f"{trabajador.nombres} {trabajador.apellidos} está en la matriz: "
                "crea o elige a quien lo reemplaza antes de darlo de baja.",
                "impacto": impacto.model_dump(mode="json"),
            },
        )

    nuevo = None
    if reemplazo_id is not None:
        if reemplazo_id == trabajador.id:
            raise HTTPException(422, "El reemplazo debe ser otra persona")
        nuevo = get_or_404(db, Trabajador, reemplazo_id, "Trabajador de reemplazo")
        if not nuevo.activo:
            raise HTTPException(422, "El trabajador de reemplazo está dado de baja")
        for p in partic:
            ocupados = {q.trabajador_id for q in p.ciclo.participantes} | {
                q.relevo_id for q in p.ciclo.participantes if q.relevo_id
            }
            if nuevo.id in ocupados:
                raise HTTPException(422, f"{nuevo.nombres} ya participa en la matriz «{p.ciclo.nombre}»")

    for p in partic:
        if p.trabajador_id == trabajador.id:
            p.trabajador_id = nuevo.id
        else:
            p.relevo_id = nuevo.id if nuevo else None

    futuras = db.query(Asignacion).filter(Asignacion.trabajador_id == trabajador.id, Asignacion.fecha >= hoy).all()
    if nuevo is not None and es_titular:
        ocupadas = {
            a.fecha for a in db.query(Asignacion).filter(Asignacion.trabajador_id == nuevo.id, Asignacion.fecha >= hoy)
        }
        for a in futuras:
            if a.fecha in ocupadas:
                db.delete(a)
            else:
                a.trabajador_id = nuevo.id
    else:
        for a in futuras:
            db.delete(a)

    for r in _reemplazos_vigentes(db, trabajador.id, hoy).all():
        r.activo = False

    trabajador.activo = False
    if usuario is not None:
        usuario.activo = False
    db.commit()
