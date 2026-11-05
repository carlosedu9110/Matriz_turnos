"""Roles (permisos) y cargos (posición laboral). Son conceptos independientes."""

# Roles: determinan los permisos dentro del sistema.
ROL_ADMIN = "Admin"
ROL_USUARIO_FINAL = "Usuario final"
ROLES = (ROL_ADMIN, ROL_USUARIO_FINAL)

# Cargos disponibles: determinan la posición del trabajador, no sus permisos.
CARGO_ANALISTA = "Analista"
CARGO_ESPECIALISTA = "Especialista"
CARGO_ADMIN = "Admin"
CARGOS = (CARGO_ANALISTA, CARGO_ESPECIALISTA, CARGO_ADMIN)

# Nombres antiguos (Fase 1) que se migran en init_db.
ROLES_LEGADOS = {"Administrador": ROL_ADMIN, "Trabajador": ROL_USUARIO_FINAL}
