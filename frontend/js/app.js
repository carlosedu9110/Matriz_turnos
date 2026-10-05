// Matriz de turnos - frontend vanilla. Todo el texto dinámico se inserta con textContent (sin innerHTML).
const $ = (id) => document.getElementById(id);
const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

const state = { isAdmin: false, matrices: [], matriz: null, anchor: new Date(), scope: "week", layout: "turno", data: null };

function el(tag, props = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v;
    else if (k === "style") n.style.cssText = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) n.setAttribute(k, v);
  }
  for (const c of children.flat()) if (c !== null && c !== undefined) n.append(c);
  return n;
}

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const parse = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
const addDays = (d, n) => { const r = new Date(d); r.setDate(r.getDate() + n); return r; };
const mondayOf = (d) => addDays(d, -((d.getDay() + 6) % 7));
const fmtShort = (d) => `${d.getDate()} ${MESES[d.getMonth()].slice(0, 3)}`;
const hhmm = (t) => t.slice(0, 5);

function toast(msg, isErr = false) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast" + (isErr ? " err" : "");
  clearTimeout(toast.h);
  toast.h = setTimeout(() => t.classList.add("hidden"), 3500);
}

// Rango visible: semanas completas (lunes a domingo). El mes muestra todas sus semanas, una debajo de otra.
function range() {
  if (state.scope === "week") {
    const s = mondayOf(state.anchor);
    return [s, addDays(s, 6)];
  }
  const a = state.anchor;
  const primero = new Date(a.getFullYear(), a.getMonth(), 1);
  const ultimo = new Date(a.getFullYear(), a.getMonth() + 1, 0);
  return [mondayOf(primero), addDays(mondayOf(ultimo), 6)];
}

function days(desde, hasta) {
  const out = [];
  for (let d = desde; d <= hasta; d = addDays(d, 1)) out.push(d);
  return out;
}

function weeksOf(dias) {
  const out = [];
  for (let i = 0; i < dias.length; i += 7) out.push(dias.slice(i, i + 7));
  return out;
}

// Color estable por persona (como en el Excel): se deriva del id del trabajador.
const PALETA = ["#548235", "#F4B183", "#00B0F0", "#FF0000", "#8E7CC3", "#E6B800", "#2E9E9E", "#D56AA0", "#7F7F7F", "#C55A11"];
const colorPersona = (id) => PALETA[id % PALETA.length];
const textoPersona = (id) => (["#F4B183", "#E6B800", "#00B0F0"].includes(colorPersona(id)) ? "#111" : "#fff");

async function load() {
  const [desde, hasta] = range();
  const a = state.anchor;
  $("range-label").textContent =
    state.scope === "week"
      ? `${fmtShort(desde)} – ${fmtShort(hasta)} ${hasta.getFullYear()}`
      : `${MESES[a.getMonth()]} ${a.getFullYear()}`;
  if (!state.matriz) { state.data = null; render(); return; }
  try {
    state.data = await Api.get(`/matriz?desde=${iso(desde)}&hasta=${iso(hasta)}&matriz=${encodeURIComponent(state.matriz)}`);
  } catch (e) {
    toast(e.message, true);
    state.data = null;
  }
  render();
}

function render() {
  const d = state.data;
  const cont = $("grid-wrap");
  cont.replaceChildren();
  $("legend").replaceChildren();
  renderAlertas();
  const vacio = !state.matriz || !d || d.celdas.length === 0;
  $("empty").classList.toggle("hidden", !vacio);
  $("empty").textContent = !state.matriz
    ? "Aún no hay ninguna matriz. Créala desde /docs (POST /matriz/ciclos) o ejecuta: python -m app.db.seed_matriz"
    : "No hay turnos en este periodo." + (state.isAdmin ? " Usa «Generar turnos»." : "");
  if (!d) return;

  const leyenda = [];
  if (state.layout === "turno") {
    const vistos = new Map();
    d.celdas.forEach((c) => vistos.set(c.trabajador.id, c.trabajador));
    [...vistos.values()]
      .sort((x, y) => x.nombres.localeCompare(y.nombres))
      .forEach((p) => leyenda.push(el("span", {}, el("i", { class: "dot", style: `background:${colorPersona(p.id)}` }), p.nombres)));
  } else {
    d.tipos_turno.forEach((t) =>
      leyenda.push(el("span", {}, el("i", { class: "dot", style: `background:${t.color || "#888"}` }), `${t.nombre} ${hhmm(t.hora_inicio)}–${hhmm(t.hora_fin)}`)));
  }
  leyenda.push(el("span", {}, el("i", { class: "dot", style: "background:#888;outline:2px dashed #444" }), "↪ Cobertura (reemplazo)"));
  $("legend").append(...leyenda);
  if (vacio) return;

  const dias = days(parse(d.desde), parse(d.hasta));
  let mesActual = null;
  for (const semana of weeksOf(dias)) {
    // Banner cuando cambia el mes (como en el Excel).
    const mes = semana[3]; // jueves: mes al que pertenece la mayoría de la semana
    const clave = `${mes.getFullYear()}-${mes.getMonth()}`;
    if (state.scope === "month" && clave !== mesActual) {
      mesActual = clave;
      cont.append(el("div", { class: "month-banner" }, `${MESES[mes.getMonth()]} ${mes.getFullYear()}`));
    }
    const tabla = el("table", { class: "week" });
    state.layout === "turno" ? renderTurno(tabla, d, semana) : renderPersona(tabla, d, semana);
    cont.append(tabla);
  }
}

function dayCls(day) {
  return iso(day) === iso(new Date()) ? "today" : day.getDay() === 0 || day.getDay() === 6 ? "weekend" : "";
}

function headRow(first, dias) {
  return el("thead", {}, el("tr", {},
    el("th", { class: "rowhead" }, first),
    dias.map((day) => el("th", { class: dayCls(day) }, DIAS[(day.getDay() + 6) % 7], el("small", {}, fmtShort(day)))),
  ));
}

function clickable(node, celda) {
  if (!state.isAdmin) return node;
  node.classList.add("clickable");
  node.addEventListener("click", () => openCelda(celda));
  return node;
}

function renderTurno(tabla, d, dias) {
  const idx = {};
  for (const c of d.celdas) (idx[`${c.fecha}|${c.tipo_turno_id}`] ||= []).push(c);
  tabla.append(headRow("TIME / DATE", dias), el("tbody", {}, d.tipos_turno.map((t) =>
    el("tr", {},
      el("td", { class: "rowhead" }, `${hhmm(t.hora_inicio)} – ${hhmm(t.hora_fin)}`, el("small", {}, t.nombre)),
      dias.map((day) => {
        const celdas = idx[`${iso(day)}|${t.id}`] || [];
        const td = el("td", { class: "person-cell " + dayCls(day) });
        celdas.forEach((c) => {
          const chip = el("div", {
            class: "person" + (c.es_reemplazo ? " cover" : "") + (c.manual ? " manual" : ""),
            style: `background:${colorPersona(c.trabajador.id)};color:${textoPersona(c.trabajador.id)}`,
            title: c.es_reemplazo ? `${c.trabajador.nombres} cubre a ${c.titular.nombres}` : `${c.trabajador.nombres} ${c.trabajador.apellidos}`,
          }, (c.es_reemplazo ? "↪ " : "") + c.trabajador.nombres);
          td.append(clickable(chip, c));
        });
        return td;
      }),
    ))));
}

function renderPersona(tabla, d, dias) {
  const tipos = Object.fromEntries(d.tipos_turno.map((t) => [t.id, t]));
  const personas = [];
  const visto = new Set();
  const add = (p, nota) => { if (p && !visto.has(p.id)) { visto.add(p.id); personas.push({ ...p, nota }); } };
  (d.ciclo?.participantes || []).forEach((p) => add(p.trabajador, `Titular · fase ${p.fase}`));
  (d.ciclo?.participantes || []).forEach((p) => add(p.relevo, `Relevo de ${p.trabajador.nombres}`));
  d.celdas.forEach((c) => { add(c.trabajador, ""); add(c.titular, ""); });

  const idx = {};
  for (const c of d.celdas) {
    if (c.titular) (idx[`${c.titular.id}|${c.fecha}`] ||= []).push({ c, ausente: true });
    (idx[`${c.trabajador.id}|${c.fecha}`] ||= []).push({ c, ausente: false });
  }
  tabla.append(headRow("Persona", dias), el("tbody", {}, personas.map((p) =>
    el("tr", {},
      el("td", { class: "rowhead", title: `${p.nombres} ${p.apellidos}` }, p.nombres, p.nota ? el("small", {}, p.nota) : null),
      dias.map((day) => el("td", { class: dayCls(day) }, (idx[`${p.id}|${iso(day)}`] || []).map(({ c, ausente }) => {
        const t = tipos[c.tipo_turno_id];
        const node = el("div", {
          class: "cell-shift" + (ausente ? " absent" : "") + (c.es_reemplazo && !ausente ? " cover" : ""),
          style: `background:${t.color || "#888"}`,
          title: ausente ? `Ausente · lo cubre ${c.trabajador.nombres}` : c.es_reemplazo ? `Cubre a ${c.titular.nombres}` : t.nombre,
        }, (c.es_reemplazo && !ausente ? "↪ " : "") + t.nombre);
        return clickable(node, c);
      }))),
    ))));
}

// ---- Diálogos ----
function openDialog(...content) {
  const dlg = $("dlg");
  dlg.classList.remove("wide");
  $("dlg-form").replaceChildren(...content.filter((c) => c !== null && c !== undefined));
  if (!dlg.open) dlg.showModal();
}
const closeDialog = () => $("dlg").close();
const cancelBtn = () => el("button", { class: "btn", type: "button", onclick: closeDialog }, "Cerrar");

async function openCelda(c) {
  const tipo = state.data.tipos_turno.find((t) => t.id === c.tipo_turno_id);
  const titulo = `${tipo.nombre} · ${fmtShort(parse(c.fecha))}`;
  if (c.es_reemplazo) {
    return openDialog(
      el("h2", {}, titulo),
      el("p", {}, `${c.trabajador.nombres} ${c.trabajador.apellidos} cubre a ${c.titular.nombres} ${c.titular.apellidos}.`),
      el("div", { class: "actions" }, cancelBtn(),
        el("button", { class: "btn danger", type: "button", onclick: async () => {
          try { await Api.del(`/reemplazos/${c.reemplazo_id}`); closeDialog(); toast("Reemplazo anulado"); load(); } catch (e) { toast(e.message, true); }
        } }, "Anular reemplazo")),
    );
  }
  let trabajadores = [];
  try { trabajadores = await Api.get("/trabajadores?activo=true&limit=500"); } catch (e) { return toast(e.message, true); }
  const part = state.data.ciclo?.participantes.find((p) => p.trabajador.id === c.trabajador.id);
  const sel = el("select", { name: "reemplazo", required: "" },
    trabajadores.filter((t) => t.id !== c.trabajador.id).map((t) =>
      el("option", { value: t.id, ...(part?.relevo?.id === t.id ? { selected: "" } : {}) }, `${t.nombres} ${t.apellidos}`)));
  const desde = el("input", { type: "date", name: "desde", value: c.fecha, required: "" });
  const hasta = el("input", { type: "date", name: "hasta", value: c.fecha, required: "" });
  const motivo = el("input", { name: "motivo", maxlength: "255", placeholder: "Incapacidad, vacaciones, permiso…" });
  const soloTurno = el("input", { type: "checkbox", checked: "" });
  openDialog(
    el("h2", {}, `Ausencia de ${c.trabajador.nombres}`),
    el("p", { class: "muted" }, titulo),
    el("label", {}, "Lo reemplaza", sel),
    el("label", {}, "Desde", desde),
    el("label", {}, "Hasta", hasta),
    el("label", {}, "Motivo", motivo),
    el("label", { style: "display:flex;gap:.5rem;align-items:center" }, soloTurno, `Solo el turno ${tipo.nombre}`),
    el("div", { class: "actions" }, cancelBtn(),
      el("button", { class: "btn primary", type: "button", onclick: async () => {
        try {
          await Api.post("/reemplazos", {
            trabajador_ausente_id: c.trabajador.id,
            trabajador_reemplazo_id: Number(sel.value),
            tipo_turno_id: soloTurno.checked ? c.tipo_turno_id : null,
            fecha_inicio: desde.value, fecha_fin: hasta.value, motivo: motivo.value || null,
          });
          closeDialog(); toast("Reemplazo registrado"); load();
        } catch (e) { toast(e.message, true); }
      } }, "Registrar")),
  );
}

function openGenerar() {
  const ciclo = state.data?.ciclo;
  if (!ciclo) return toast("Selecciona una matriz existente", true);
  const lunes = mondayOf(new Date());
  const desde = el("input", { type: "date", value: iso(lunes) });
  const hasta = el("input", { type: "date", value: iso(addDays(lunes, 12 * 7 - 1)) });
  const sobre = el("input", { type: "checkbox" });
  openDialog(
    el("h2", {}, `Generar turnos · ${ciclo.nombre}`),
    el("p", { class: "muted" }, "Aplica el ciclo rotativo de 4 semanas. No modifica asignaciones manuales (✎)."),
    el("label", {}, "Desde", desde), el("label", {}, "Hasta", hasta),
    el("label", { style: "display:flex;gap:.5rem;align-items:center" }, sobre, "Sobrescribir turnos ya generados"),
    el("div", { class: "actions" }, cancelBtn(),
      el("button", { class: "btn primary", type: "button", onclick: async () => {
        try {
          const r = await Api.post(`/matriz/ciclos/${ciclo.id}/generar`, { desde: desde.value, hasta: hasta.value, sobrescribir: sobre.checked });
          closeDialog(); toast(`Turnos generados: ${r.creadas} nuevos, ${r.actualizadas} actualizados`); load();
        } catch (e) { toast(e.message, true); }
      } }, "Generar")),
  );
}

// ---- Personal: altas, accesos y bajas ----
const inputEl = (name, label, attrs = {}) => {
  const input = el("input", { name, ...attrs });
  return { input, label: el("label", {}, label, input) };
};

function formAcceso() {
  const u = inputEl("username", "Usuario", { minlength: "3", maxlength: "50" });
  const e = inputEl("email", "Correo", { type: "email" });
  const p = inputEl("password", "Contraseña (mín. 8)", { type: "password", minlength: "8", autocomplete: "new-password" });
  const rol = el("select", {}, el("option", { value: "Trabajador" }, "Trabajador"), el("option", { value: "Administrador" }, "Administrador"));
  return {
    nodes: [u.label, e.label, p.label, el("label", {}, "Rol", rol)],
    valor: () => ({ username: u.input.value.trim(), email: e.input.value.trim(), password: p.input.value, rol: rol.value }),
  };
}

async function refrescarMatriz() {
  try { state.matrices = await Api.get("/matriz/ciclos"); } catch (_) { /* se conserva la lista previa */ }
  await load();
}

async function openPersonal() {
  let lista;
  try { lista = await Api.get("/trabajadores?limit=500"); } catch (e) { return toast(e.message, true); }
  const accion = (texto, fn, cls = "") => el("button", { class: `btn ${cls}`, type: "button", onclick: fn }, texto);
  const filas = lista.map((t) => el("tr", {},
    el("td", {}, `${t.nombres} ${t.apellidos}`, el("br"), el("small", {}, t.documento)),
    el("td", {}, el("span", { class: "badge " + (t.activo ? "ok" : "off") }, t.activo ? "Activo" : "De baja")),
    el("td", {}, t.tiene_usuario ? "Con acceso" : "Sin acceso"),
    el("td", {}, el("div", { class: "row-actions" }, ...(t.activo
      ? [
          t.tiene_usuario ? accion("Quitar acceso", () => openQuitarAcceso(t)) : accion("Dar acceso", () => openDarAcceso(t)),
          accion("Dar de baja", () => bajaFlow(t), "danger"),
        ]
      : [accion("Reactivar", async () => {
          try { await Api.patch(`/trabajadores/${t.id}`, { activo: true }); toast("Trabajador reactivado"); openPersonal(); }
          catch (e) { toast(e.message, true); }
        })]))),
  ));
  openDialog(
    el("h2", {}, "Personal"),
    el("div", { class: "actions", style: "justify-content:space-between" },
      el("span", { class: "muted" }, `${lista.length} personas`),
      accion("＋ Nuevo trabajador", () => openNuevoTrabajador(openPersonal), "primary")),
    el("table", { class: "personal-table" },
      el("thead", {}, el("tr", {}, el("th", {}, "Nombre"), el("th", {}, "Estado"), el("th", {}, "Acceso"), el("th", {}, ""))),
      el("tbody", {}, filas)),
    el("div", { class: "actions" }, cancelBtn()),
  );
  $("dlg").classList.add("wide");
}

function openNuevoTrabajador(volver) {
  const doc = inputEl("documento", "Documento", { required: "", maxlength: "30" });
  const nom = inputEl("nombres", "Nombres", { required: "", maxlength: "100" });
  const ape = inputEl("apellidos", "Apellidos", { required: "", maxlength: "100" });
  const chk = el("input", { type: "checkbox" });
  const acceso = formAcceso();
  const cont = el("div", { class: "hidden", style: "display:grid;gap:.7rem" }, ...acceso.nodes);
  chk.addEventListener("change", () => cont.classList.toggle("hidden", !chk.checked));
  openDialog(
    el("h2", {}, "Nuevo trabajador"),
    doc.label, nom.label, ape.label,
    el("label", { style: "display:flex;gap:.5rem;align-items:center" }, chk, "Crear acceso al sistema"),
    cont,
    el("div", { class: "actions" }, el("button", { class: "btn", type: "button", onclick: volver }, "Volver"),
      el("button", { class: "btn primary", type: "button", onclick: async () => {
        const body = { documento: doc.input.value.trim(), nombres: nom.input.value.trim(), apellidos: ape.input.value.trim() };
        if (chk.checked) body.usuario = acceso.valor();
        try { await Api.post("/trabajadores", body); toast("Trabajador creado"); volver(); }
        catch (e) { toast(e.message, true); }
      } }, "Crear")),
  );
}

function openDarAcceso(t) {
  const acceso = formAcceso();
  openDialog(
    el("h2", {}, `Dar acceso a ${t.nombres} ${t.apellidos}`),
    ...acceso.nodes,
    el("div", { class: "actions" }, el("button", { class: "btn", type: "button", onclick: openPersonal }, "Volver"),
      el("button", { class: "btn primary", type: "button", onclick: async () => {
        try { await Api.post(`/trabajadores/${t.id}/usuario`, acceso.valor()); toast("Acceso creado"); openPersonal(); }
        catch (e) { toast(e.message, true); }
      } }, "Crear acceso")),
  );
}

function openQuitarAcceso(t) {
  openDialog(
    el("h2", {}, `Quitar acceso a ${t.nombres} ${t.apellidos}`),
    el("p", {}, "Se elimina su usuario y contraseña. La persona y su historial en la matriz se conservan."),
    el("div", { class: "actions" }, el("button", { class: "btn", type: "button", onclick: openPersonal }, "Volver"),
      el("button", { class: "btn danger", type: "button", onclick: async () => {
        try { await Api.del(`/trabajadores/${t.id}/usuario`); toast("Acceso eliminado"); openPersonal(); }
        catch (e) { toast(e.message, true); }
      } }, "Quitar acceso")),
  );
}

// Baja: si la persona está en la matriz se advierte y se exige crear o elegir a quien la reemplaza.
async function bajaFlow(t) {
  const nombre = `${t.nombres} ${t.apellidos}`;
  let imp;
  try { imp = await Api.get(`/trabajadores/${t.id}/impacto`); } catch (e) { return toast(e.message, true); }
  const terminar = async (qs, msg) => {
    try {
      await Api.del(`/trabajadores/${t.id}${qs}`);
      toast(msg);
      refrescarMatriz();
      openPersonal();
    } catch (e) { toast(e.message, true); }
  };
  const volver = el("button", { class: "btn", type: "button", onclick: openPersonal }, "Volver");

  if (!imp.en_matriz) {
    return openDialog(
      el("h2", {}, `Dar de baja a ${nombre}`),
      el("p", {}, "Quedará inactivo y se bloqueará su acceso; su historial se conserva." +
        (imp.asignaciones_futuras ? ` Se quitarán ${imp.asignaciones_futuras} turnos futuros.` : "") +
        (imp.reemplazos_activos ? ` Se anularán ${imp.reemplazos_activos} reemplazos vigentes.` : "")),
      el("div", { class: "actions" }, volver,
        el("button", { class: "btn danger", type: "button", onclick: () => terminar("", "Trabajador dado de baja") }, "Dar de baja")),
    );
  }

  const esTitular = imp.posiciones.some((p) => p.rol === "titular");
  let candidatos = [];
  try { candidatos = (await Api.get("/trabajadores?activo=true&limit=500")).filter((x) => x.id !== t.id); }
  catch (e) { return toast(e.message, true); }
  const enCiclo = new Set();
  (state.data?.ciclo?.participantes || []).forEach((p) => { enCiclo.add(p.trabajador.id); if (p.relevo) enCiclo.add(p.relevo.id); });
  const sel = el("select", {}, el("option", { value: "" }, "— Elige quién lo reemplaza —"),
    ...candidatos.filter((x) => !enCiclo.has(x.id)).map((x) => el("option", { value: x.id }, `${x.nombres} ${x.apellidos}`)));

  const doc = inputEl("documento", "Documento", { maxlength: "30" });
  const nom = inputEl("nombres", "Nombres", { maxlength: "100" });
  const ape = inputEl("apellidos", "Apellidos", { maxlength: "100" });
  const nuevo = el("details", { class: "nuevo" }, el("summary", {}, "＋ Crear un trabajador nuevo como reemplazo"),
    doc.label, nom.label, ape.label,
    el("button", { class: "btn", type: "button", onclick: async () => {
      try {
        const n = await Api.post("/trabajadores", { documento: doc.input.value.trim(), nombres: nom.input.value.trim(), apellidos: ape.input.value.trim() });
        const op = el("option", { value: n.id }, `${n.nombres} ${n.apellidos}`);
        sel.append(op);
        sel.value = String(n.id);
        nuevo.open = false;
        toast("Trabajador creado y seleccionado como reemplazo");
      } catch (e) { toast(e.message, true); }
    } }, "Crear y seleccionar"));

  const sinRelevo = el("input", { type: "checkbox" });
  openDialog(
    el("h2", {}, `Dar de baja a ${nombre}`),
    el("div", { class: "warn" },
      `⚠ ${t.nombres} está en la matriz. Si sale sin reemplazo, los turnos quedan sin cubrir:`,
      el("ul", {}, imp.posiciones.map((p) => el("li", {},
        `${p.ciclo_nombre}: ` + (p.rol === "titular" ? `titular (fase ${p.fase})` : `relevo de ${p.titular}`)))),
      imp.asignaciones_futuras ? el("div", {}, `Tiene ${imp.asignaciones_futuras} turnos futuros.`) : null,
      imp.reemplazos_activos ? el("div", {}, `Tiene ${imp.reemplazos_activos} reemplazos vigentes (se anularán).`) : null),
    el("label", {}, "Reemplazo", sel),
    nuevo,
    esTitular ? null : el("label", { style: "display:flex;gap:.5rem;align-items:center" }, sinRelevo, "Dejar el puesto de relevo sin cubrir"),
    el("div", { class: "actions" }, volver,
      el("button", { class: "btn danger", type: "button", onclick: () => {
        if (sel.value) return terminar(`?reemplazo_id=${sel.value}`, "Reemplazo aplicado y trabajador dado de baja");
        if (!esTitular && sinRelevo.checked) return terminar("?sin_relevo=true", "Trabajador dado de baja (relevo sin cubrir)");
        toast("Elige o crea a quien lo reemplaza", true);
      } }, "Reemplazar y dar de baja")),
  );
}

// Aviso en la matriz si algún titular o relevo está dado de baja.
function renderAlertas() {
  const al = $("alertas");
  const faltan = [];
  (state.data?.ciclo?.participantes || []).forEach((p) => {
    if (!p.trabajador.activo) faltan.push(`${p.trabajador.nombres} (titular, fase ${p.fase})`);
    if (p.relevo && !p.relevo.activo) faltan.push(`${p.relevo.nombres} (relevo de ${p.trabajador.nombres})`);
  });
  al.classList.toggle("hidden", faltan.length === 0);
  al.textContent = faltan.length
    ? `⚠ Hay personas dadas de baja en la matriz: ${faltan.join("; ")}. ` +
      (state.isAdmin ? "Reemplázalas desde «Personal»." : "Avisa a un administrador.")
    : "";
}

// ---- Arranque ----
function bindSegmented(id, key) {
  $(id).addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    state[key] = b.dataset.v;
    [...$(id).children].forEach((x) => x.classList.toggle("active", x === b));
    key === "scope" ? load() : render();
  });
}

function shift(dir) {
  const a = new Date(state.anchor);
  state.scope === "week" ? a.setDate(a.getDate() + 7 * dir) : (a.setDate(1), a.setMonth(a.getMonth() + dir));
  state.anchor = a;
  load();
}

async function startApp() {
  $("login-view").classList.add("hidden");
  $("app-view").classList.remove("hidden");
  const me = await Api.get("/auth/me");
  state.isAdmin = me.roles.some((r) => r.nombre === "Administrador");
  $("user-label").textContent = `${me.username} · ${me.roles.map((r) => r.nombre).join(", ")}`;
  document.querySelectorAll(".admin-only").forEach((n) => n.classList.toggle("hidden", !state.isAdmin));
  state.matrices = await Api.get("/matriz/ciclos");
  const sel = $("matriz-select");
  sel.replaceChildren(...state.matrices.map((m) => el("option", { value: m.codigo }, m.nombre)));
  state.matriz = state.matrices[0]?.codigo || null;
  sel.classList.toggle("hidden", state.matrices.length < 2);
  sel.onchange = () => { state.matriz = sel.value; load(); };
  load();
}

document.addEventListener("DOMContentLoaded", () => {
  bindSegmented("scope", "scope");
  bindSegmented("layout", "layout");
  $("prev").onclick = () => shift(-1);
  $("next").onclick = () => shift(1);
  $("today").onclick = () => { state.anchor = new Date(); load(); };
  $("generate").onclick = openGenerar;
  $("personal").onclick = openPersonal;
  $("dlg-form").addEventListener("submit", (e) => e.preventDefault());
  $("dlg").addEventListener("close", () => $("dlg").classList.remove("wide"));
  $("logout").onclick = () => { Api.setToken(null); location.reload(); };
  $("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      const r = await Api.post("/auth/login", { username: f.get("username"), password: f.get("password") });
      Api.setToken(r.access_token);
      startApp();
    } catch (err) { $("login-error").textContent = err.message; }
  });
  if (Api.token) startApp().catch(() => { Api.setToken(null); $("login-view").classList.remove("hidden"); $("app-view").classList.add("hidden"); });
  else $("login-view").classList.remove("hidden");
});
