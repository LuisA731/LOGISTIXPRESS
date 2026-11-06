'use strict';

/* ==========================================================================
   LogistiXpress · núcleo del dashboard
   Mantiene el lenguaje visual del dashboard original (sidebar, topbar,
   tarjetas KPI, paneles y tablas) y lo conecta a FastAPI.
   ========================================================================== */

const API_BASE = (() => {
  if (location.protocol === 'file:') return 'http://127.0.0.1:8000/api';
  if (['5500', '5501', '5502'].includes(location.port)) return 'http://127.0.0.1:8000/api';
  return '/api';
})();

const ROL_LABEL = { admin: 'Administrador', operador: 'Operador', auditor: 'Auditor' };

const ESTADOS = {
  PLANIFICADA: ['planificada', 'Planificada'],
  EN_RUTA: ['en-ruta', 'En ruta'],
  COMPLETADA: ['completada', 'Completada'],
  CANCELADA: ['cancelada', 'Cancelada'],
  LISTO: ['listo', 'Listo'],
  ASIGNADO: ['asignado', 'Asignado'],
  EN_PICKING: ['asignado', 'En picking'],
  PICKING_COMPLETO: ['planificada', 'Picking completo'],
  EMPACADO: ['reprogramado', 'Empacado'],
  PROGRAMADA: ['planificada', 'Programada'],
  EN_RECEPCION: ['asignado', 'En recepción'],
  RECIBIDA: ['completada', 'Recibida'],
  CON_INCIDENCIA: ['fallido', 'Con incidencia'],
  PENDIENTE: ['planificada', 'Pendiente'],
  PICKEADO: ['completada', 'Pickeado'],
  FALTANTE: ['fallido', 'Faltante'],
  ENTREGADO: ['entregado', 'Entregado'],
  FALLIDO: ['fallido', 'Fallido'],
  REPROGRAMADO: ['reprogramado', 'Reprogramado'],
  DEVUELTO: ['devuelto', 'Devuelto'],
  EN_BODEGA: ['en-bodega', 'En bodega'],
  RECIBIDO: ['en-bodega', 'Recibido'],
  ETIQUETADO: ['planificada', 'Etiquetado'],
  CANCELADO: ['cancelada', 'Cancelado'],
  BORRADOR: ['simple', 'Borrador'],
};

const estado = {
  token: localStorage.getItem('royal_token') || '',
  usuario: leerJson('royal_usuario'),
  seccion: 'inicio',
  version: 0,
  rutasCache: [],
  filtroRutas: 'todas',
  rastreoGuia: '',
  abrirMovimiento: false,
  ultimoPanel: null,
  reportesHistorial: leerJson('royal_reportes', sessionStorage) || [],
};

const PAGINAS = {};

/* --------------------------------------------------------------------------
   Utilidades
   -------------------------------------------------------------------------- */
function $(selector, raiz = document) { return raiz.querySelector(selector); }
function $$(selector, raiz = document) { return [...raiz.querySelectorAll(selector)]; }

function leerJson(clave, almacen = localStorage) {
  try { return JSON.parse(almacen.getItem(clave) || 'null'); } catch { return null; }
}

function esc(valor) {
  return String(valor ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function ico(nombre, clase = '') {
  return `<svg class="ico ${clase}" aria-hidden="true"><use href="#i-${nombre}"></use></svg>`;
}

function iniciales(nombre) {
  const partes = String(nombre || '').trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return '--';
  return (partes[0][0] + (partes[1]?.[0] || '')).toUpperCase();
}

function fechaCorta(valor) {
  if (!valor) return '—';
  const fecha = new Date(String(valor).length === 10 ? `${valor}T12:00:00` : valor);
  if (Number.isNaN(fecha.getTime())) return '—';
  return fecha.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' });
}

function fechaHora(valor) {
  if (!valor) return '—';
  const fecha = new Date(valor);
  if (Number.isNaN(fecha.getTime())) return '—';
  return fecha.toLocaleString('es-MX', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

function fechaLarga(valor = new Date()) {
  const fecha = valor instanceof Date
    ? valor
    : new Date(String(valor).length === 10 ? `${valor}T12:00:00` : valor);
  return fecha.toLocaleDateString('es-MX', {
    weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
  });
}

function hoyISO() {
  const ahora = new Date();
  const local = new Date(ahora.getTime() - ahora.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function mananaISO() {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + 1);
  const local = new Date(fecha.getTime() - fecha.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function numero(valor, decimales = 0) {
  const n = Number(valor);
  if (!Number.isFinite(n)) return '—';
  return n.toLocaleString('es-MX', {
    minimumFractionDigits: decimales, maximumFractionDigits: decimales,
  });
}

function peso(valor) { return `${numero(valor, 1)} kg`; }
function volumen(valor) { return `${numero(valor, 2)} m³`; }
function porcentaje(valor) { return `${numero(valor, 1)}%`; }
function plural(cantidad, singular, plural_) {
  return `${numero(cantidad)} ${Number(cantidad) === 1 ? singular : plural_}`;
}

function opciones(valores, actual, etiqueta = (valor) => valor) {
  return valores.map((valor) => (
    `<option value="${esc(valor)}" ${String(valor) === String(actual) ? 'selected' : ''}>${esc(etiqueta(valor))}</option>`
  )).join('');
}

function claseEstado(valor) {
  return ESTADOS[String(valor || '').toUpperCase()]?.[0] || 'simple';
}

function badgeEstado(valor, etiqueta = null) {
  const clave = String(valor || '').toUpperCase();
  const info = ESTADOS[clave] || ['simple', valor || '—'];
  return `<span class="badge ${info[0]}">${esc(etiqueta || info[1])}</span>`;
}

function badgeZona(zona) {
  return `<span class="badge badge-zone">${esc(zona || '—')}</span>`;
}

function badgeRol(rol) {
  return `<span class="badge badge-role-${esc(rol)}">${esc(ROL_LABEL[rol] || rol)}</span>`;
}

function iconoEstado(valor) {
  const mapa = {
    ENTREGADO: 'check', EN_RUTA: 'flota', FALLIDO: 'alerta', DEVUELTO: 'inventario',
    REPROGRAMADO: 'calendario', ASIGNADO: 'rutas', ETIQUETADO: 'paquete',
    RECIBIDO: 'inventario', PLANIFICADA: 'calendario', COMPLETADA: 'check',
    CANCELADA: 'x',
  };
  return mapa[String(valor || '').toUpperCase()] || 'paquete';
}

function vigente(version) { return version === estado.version; }

function bloquear(boton, texto = 'Procesando…') {
  if (!boton) return () => {};
  const original = boton.innerHTML;
  boton.disabled = true;
  boton.innerHTML = `<span class="spinner"></span>${texto}`;
  return () => { boton.disabled = false; boton.innerHTML = original; };
}

/* --------------------------------------------------------------------------
   Toasts, modales y componentes
   -------------------------------------------------------------------------- */
function toast(mensaje, tipo = 'info', duracion = 4200) {
  const contenedor = $('#toastContainer');
  const icono = tipo === 'success' ? 'check' : tipo === 'error' ? 'alerta' : 'campana';
  const nodo = document.createElement('div');
  nodo.className = `toast ${tipo}`;
  nodo.innerHTML = `${ico(icono)}<span>${esc(mensaje)}</span>`;
  contenedor.appendChild(nodo);
  setTimeout(() => {
    nodo.style.opacity = '0';
    nodo.style.transform = 'translateY(6px)';
    nodo.style.transition = 'opacity .2s, transform .2s';
    setTimeout(() => nodo.remove(), 220);
  }, duracion);
}

let modalActual = null;

function abrirModal({ titulo, subtitulo = '', cuerpo = '', acciones = '', ancho = '' }) {
  cerrarModal();
  const raiz = $('#modalRoot');
  raiz.innerHTML = `
    <div class="modal-overlay" id="modalOverlay">
      <section class="modal ${ancho}" role="dialog" aria-modal="true" aria-labelledby="modalTitulo">
        <header class="modal-header">
          <div>
            <h2 id="modalTitulo">${esc(titulo)}</h2>
            ${subtitulo ? `<p>${esc(subtitulo)}</p>` : ''}
          </div>
          <button class="modal-close" id="modalClose" type="button" aria-label="Cerrar">${ico('x')}</button>
        </header>
        <div class="modal-body">${cuerpo}</div>
        <footer class="modal-footer">${acciones}</footer>
      </section>
    </div>`;
  document.body.classList.add('no-scroll');
  const overlay = $('#modalOverlay');
  overlay.addEventListener('click', (evento) => {
    if (evento.target === overlay) cerrarModal();
  });
  $('#modalClose').onclick = cerrarModal;
  modalActual = overlay;
  return overlay;
}

function cerrarModal() {
  $('#modalRoot').innerHTML = '';
  document.body.classList.remove('no-scroll');
  modalActual = null;
}

function kpiCard({ clase = 'blue', icono: nombreIcono, etiqueta, valor, detalle = '' }) {
  return `
    <article class="kpi-card kpi-${clase}">
      <div class="kpi-top"><span class="kpi-icon">${ico(nombreIcono)}</span></div>
      <span class="kpi-label">${esc(etiqueta)}</span>
      <strong class="kpi-value">${valor}</strong>
      ${detalle ? `<span class="kpi-sub">${esc(detalle)}</span>` : ''}
    </article>`;
}

function encabezadoPanel(titulo, subtitulo, acciones = '') {
  return `
    <div class="panel-header">
      <div><h2>${esc(titulo)}</h2>${subtitulo ? `<p>${esc(subtitulo)}</p>` : ''}</div>
      ${acciones ? `<div class="panel-header-actions">${acciones}</div>` : ''}
    </div>`;
}

function esqueletoPagina() {
  return `
    <div class="grid grid-kpi">
      ${Array.from({ length: 4 }, () => '<div class="skeleton skeleton-card"></div>').join('')}
    </div>
    <div class="skeleton skeleton-panel section-gap"></div>
    <div class="skeleton skeleton-panel section-gap"></div>`;
}

function paginaError(error) {
  return `
    <div class="panel panel-pad">
      <div class="empty-state">
        ${ico('alerta')}
        <h3>No se pudo cargar esta sección</h3>
        <p>${esc(error?.message || 'Ocurrió un error inesperado.')}</p>
        <button class="btn btn-primary" type="button" id="retryPage">${ico('refrescar')} Reintentar</button>
      </div>
    </div>`;
}

function estadoVacio(icono, titulo, mensaje, accion = '') {
  return `<div class="empty-state">${ico(icono)}<h3>${esc(titulo)}</h3><p>${esc(mensaje)}</p>${accion}</div>`;
}

/* --------------------------------------------------------------------------
   API
   -------------------------------------------------------------------------- */
async function api(ruta, opciones = {}) {
  const { permitir401 = false, ...resto } = opciones;
  const cabeceras = { ...(resto.headers || {}) };
  if (estado.token) cabeceras.Authorization = `Bearer ${estado.token}`;
  if (resto.body && !(resto.body instanceof FormData) && !cabeceras['Content-Type']) {
    cabeceras['Content-Type'] = 'application/json';
  }
  let respuesta;
  try {
    respuesta = await fetch(`${API_BASE}${ruta}`, { ...resto, headers: cabeceras });
  } catch {
    throw new Error('No se pudo conectar con la API local. Verifica que FastAPI esté corriendo.');
  }
  const tipo = respuesta.headers.get('content-type') || '';
  const datos = tipo.includes('application/json')
    ? await respuesta.json().catch(() => null)
    : await respuesta.text().catch(() => '');
  if (!respuesta.ok) {
    if (respuesta.status === 401 && !permitir401) {
      const sesionExistia = Boolean(estado.token);
      limpiarSesion();
      mostrarLogin();
      if (sesionExistia) toast('Tu sesión expiró. Vuelve a iniciar sesión.', 'error');
    }
    const detalle = datos?.detail ?? datos ?? `Error ${respuesta.status}`;
    const mensaje = typeof detalle === 'string'
      ? detalle
      : Array.isArray(detalle)
        ? detalle.map((item) => item?.msg || String(item)).join(' · ')
        : (detalle?.mensaje || `Error ${respuesta.status}`);
    const error = new Error(mensaje);
    error.datos = datos;
    error.status = respuesta.status;
    throw error;
  }
  return datos;
}

async function apiBlob(ruta) {
  const cabeceras = {};
  if (estado.token) cabeceras.Authorization = `Bearer ${estado.token}`;
  let respuesta;
  try {
    respuesta = await fetch(`${API_BASE}${ruta}`, { headers: cabeceras });
  } catch {
    throw new Error('No se pudo conectar con la API local.');
  }
  if (!respuesta.ok) {
    let mensaje = `Error ${respuesta.status}`;
    try {
      const datos = await respuesta.json();
      mensaje = typeof datos.detail === 'string'
        ? datos.detail
        : (datos.detail?.mensaje || mensaje);
    } catch { /* sin cuerpo JSON */ }
    if (respuesta.status === 401) {
      limpiarSesion();
      mostrarLogin();
      toast('Tu sesión expiró. Vuelve a iniciar sesión.', 'error');
    }
    throw new Error(mensaje);
  }
  return respuesta.blob();
}

async function descargarBlob(blob, nombre) {
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement('a');
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

/* --------------------------------------------------------------------------
   Sesión y navegación
   -------------------------------------------------------------------------- */
function guardarSesion(token, usuario) {
  estado.token = token;
  estado.usuario = usuario;
  localStorage.setItem('royal_token', token);
  localStorage.setItem('royal_usuario', JSON.stringify(usuario));
}

function limpiarSesion() {
  estado.token = '';
  estado.usuario = null;
  localStorage.removeItem('royal_token');
  localStorage.removeItem('royal_usuario');
  estado.rutasCache = [];
  estado.rastreoGuia = '';
}

function esAdmin() { return estado.usuario?.rol === 'admin'; }
function puedeOperar() { return ['admin', 'operador'].includes(estado.usuario?.rol); }

function actualizarUIUsuario() {
  const usuario = estado.usuario;
  if (!usuario) return;
  const rol = ROL_LABEL[usuario.rol] || usuario.rol;
  const inicial = iniciales(usuario.nombre);
  $('#userAvatar').textContent = inicial;
  $('#topAvatar').textContent = inicial;
  $('#userName').textContent = usuario.nombre;
  $('#userRole').textContent = `${rol} · ${usuario.puesto || usuario.usuario}`;
  $('#topUserName').textContent = usuario.nombre;
  $('#topUserRole').textContent = rol;
}

function aplicarPermisosNav() {
  $$('.nav-link[data-role]').forEach((boton) => {
    const permitidos = boton.dataset.role.split(/\s+/);
    boton.hidden = !permitidos.includes(estado.usuario?.rol);
  });
}

function mostrarLogin() {
  cerrarModal();
  $('#appShell').hidden = true;
  $('#loginView').hidden = false;
  $('#loginError').textContent = '';
  document.body.classList.remove('no-scroll');
  setTimeout(() => $('#loginUsuario')?.focus(), 30);
}

function mostrarApp() {
  $('#loginView').hidden = true;
  $('#appShell').hidden = false;
  actualizarUIUsuario();
  aplicarPermisosNav();
  procesarHash();
}

function actualizarNavActivo() {
  $$('#mainNav .nav-link').forEach((boton) => {
    boton.classList.toggle('active', boton.dataset.section === estado.seccion);
  });
}

function navegar(seccion) {
  if (seccion !== 'rastreo') estado.rastreoGuia = '';
  const destino = `#/${seccion}`;
  if (location.hash === destino) renderSeccion();
  else location.hash = destino;
  $('#sidebar').classList.remove('open');
}

function irARastreo(guia) {
  const limpia = String(guia || '').trim().toUpperCase();
  if (!limpia) { toast('Escribe una guía para rastrear el paquete.', 'info'); return; }
  estado.rastreoGuia = limpia;
  if (estado.seccion === 'rastreo') renderSeccion();
  else location.hash = '#/rastreo';
}

function procesarHash() {
  const crudo = location.hash.replace(/^#\/?/, '');
  const [seccion, parametro] = crudo.split('/');
  if (seccion === 'rastreo' && parametro) {
    estado.rastreoGuia = decodeURIComponent(parametro).toUpperCase();
  }
  estado.seccion = PAGINAS[seccion] ? seccion : 'inicio';
  renderSeccion();
}

async function renderSeccion() {
  const version = ++estado.version;
  actualizarNavActivo();
  const contenido = $('#appContent');
  const pagina = PAGINAS[estado.seccion];
  if (!pagina) { location.hash = '#/inicio'; return; }
  contenido.innerHTML = esqueletoPagina();
  try {
    await pagina(version);
    if (vigente(version)) contenido.focus({ preventScroll: true });
  } catch (error) {
    if (!vigente(version)) return;
    contenido.innerHTML = paginaError(error);
    toast(error.message || 'No se pudo cargar la sección.', 'error');
    $('#retryPage')?.addEventListener('click', renderSeccion);
  }
  if (window.innerWidth <= 1020) $('#sidebar').classList.remove('open');
}

async function ingresar(usuario, contrasena) {
  const boton = $('#loginButton');
  const restaurar = bloquear(boton, 'Validando…');
  $('#loginError').textContent = '';
  try {
    const datos = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ usuario, contrasena }),
      permitir401: true,
    });
    guardarSesion(datos.token, datos.usuario);
    mostrarApp();
    toast(`Bienvenido, ${datos.usuario.nombre}.`, 'success');
  } catch (error) {
    $('#loginError').textContent = error.message;
  } finally {
    restaurar();
  }
}

async function salir() {
  try { await api('/auth/logout', { method: 'POST', permitir401: true }); } catch { /* sesión local */ }
  limpiarSesion();
  history.replaceState(null, '', location.pathname);
  mostrarLogin();
  toast('Sesión cerrada.', 'info');
}

/* --------------------------------------------------------------------------
   Enlaces globales
   -------------------------------------------------------------------------- */
function bindLogin() {
  $('#loginForm').addEventListener('submit', (evento) => {
    evento.preventDefault();
    ingresar($('#loginUsuario').value.trim(), $('#loginContrasena').value);
  });
  $$('.demo-user').forEach((boton) => {
    boton.addEventListener('click', () => {
      $('#loginUsuario').value = boton.dataset.demoUsuario;
      $('#loginContrasena').value = boton.dataset.demoContrasena;
      $('#loginForm').requestSubmit();
    });
  });
}

function bindShell() {
  $('#mainNav').addEventListener('click', (evento) => {
    const boton = evento.target.closest('[data-section]');
    if (!boton || boton.hidden) return;
    navegar(boton.dataset.section);
  });
  $('#menuButton').addEventListener('click', () => $('#sidebar').classList.toggle('open'));
  $('#logoutButton').addEventListener('click', salir);
  $('#userMini').addEventListener('click', () => navegar('perfil'));
  $('#topUser').addEventListener('click', () => navegar('perfil'));
  $('#searchForm').addEventListener('submit', (evento) => {
    evento.preventDefault();
    irARastreo($('#searchInput').value);
    $('#searchInput').value = '';
  });
  $('#notificationButton').addEventListener('click', abrirActividadReciente);
  window.addEventListener('hashchange', procesarHash);
  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape' && modalActual) cerrarModal();
  });
}

async function abrirActividadReciente() {
  try {
    const panel = estado.ultimoPanel || await api('/panel/resumen');
    const eventos = panel.eventos_recientes || [];
    const cuerpo = eventos.length
      ? `<div class="activity-list">${eventos.map((evento) => `
          <div class="activity-item">
            <div class="activity-icon">${ico(iconoEstado(evento.estado))}</div>
            <div class="activity-copy">
              <strong>${esc(evento.descripcion)}</strong>
              <small>${esc(evento.guia || 'Paquete')} · ${esc(evento.ubicacion || 'CEDIS')}</small>
            </div>
            <span class="activity-time">${esc(fechaHora(evento.fecha))}</span>
          </div>`).join('')}</div>`
      : estadoVacio('campana', 'Sin actividad reciente', 'Cuando se muevan paquetes verás el registro aquí.');
    abrirModal({
      titulo: 'Actividad reciente',
      subtitulo: 'Últimos eventos de rastreo registrados en el CEDIS.',
      cuerpo,
      acciones: '<button class="btn btn-ghost" type="button" id="cerrarActividad">Cerrar</button>',
      ancho: 'narrow',
    });
    $('#cerrarActividad').onclick = cerrarModal;
  } catch (error) {
    toast(error.message, 'error');
  }
}
