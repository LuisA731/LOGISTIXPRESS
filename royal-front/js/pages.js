'use strict';

/* ==========================================================================
   Páginas del dashboard
   ========================================================================== */

/* --------------------------------------------------------------------------
   Inicio
   -------------------------------------------------------------------------- */
PAGINAS.inicio = async function (version) {
  const panel = await api('/panel/resumen');
  if (!vigente(version)) return;
  estado.ultimoPanel = panel;

  const hora = new Date().getHours();
  const saludo = hora < 12 ? 'Buen día' : hora < 19 ? 'Buenas tardes' : 'Buenas noches';
  const entregas = Number(panel.entregas_hoy || 0) + Number(panel.fallidas_hoy || 0);
  const pctEntregas = entregas ? Math.round((panel.entregas_hoy / entregas) * 100) : 0;
  const pctRutas = panel.rutas_hoy ? Math.round((panel.rutas_en_ruta / panel.rutas_hoy) * 100) : 0;
  const rutasRecientes = panel.rutas_recientes || [];
  const eventos = panel.eventos_recientes || [];

  const tablaRutas = rutasRecientes.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Ruta</th><th>Zona</th><th>Conductor</th><th>Paradas</th><th>Distancia</th><th>Estado</th><th></th></tr></thead>
        <tbody>${rutasRecientes.map((ruta) => `
          <tr>
            <td class="primary-cell">${esc(ruta.folio)}<span class="sub">${esc(fechaCorta(ruta.fecha))}</span></td>
            <td>${badgeZona(ruta.zona)}</td>
            <td>${esc(ruta.conductor.nombre)}<span class="sub">${esc(ruta.vehiculo.placas)}</span></td>
            <td>${numero(ruta.num_paradas)}<span class="sub">${plural(ruta.num_bultos, 'bulto', 'bultos')}</span></td>
            <td>${numero(ruta.distancia_km, 1)} km<span class="sub">ahorro ${porcentaje(ruta.ahorro_pct)}</span></td>
            <td>${badgeEstado(ruta.estado)}</td>
            <td class="text-right"><button class="btn btn-small btn-ghost" type="button" data-ruta-detalle="${ruta.id}">Ver</button></td>
          </tr>`).join('')}
        </tbody></table></div>`
    : estadoVacio('rutas', 'Todavía no hay rutas', 'Genera el plan del día para consolidar los pedidos listos en viajes por zona.');

  const actividad = eventos.length
    ? `<div class="activity-list">${eventos.map((evento) => `
        <div class="activity-item">
          <div class="activity-icon">${ico(iconoEstado(evento.estado))}</div>
          <div class="activity-copy">
            <strong>${esc(evento.descripcion)}</strong>
            <small>${esc(evento.guia || 'Paquete')} · ${esc(evento.ubicacion || 'CEDIS')}</small>
          </div>
          <span class="activity-time">${esc(fechaHora(evento.fecha))}</span>
        </div>`).join('')}</div>`
    : estadoVacio('campana', 'Sin actividad reciente', 'Los movimientos de paquetes aparecerán aquí.');

  $('#appContent').innerHTML = `
    <section class="home-hero">
      <div>
        <p class="eyebrow">Panel principal · CEDIS Norte</p>
        <h1>${saludo}, ${esc(estado.usuario?.nombre?.split(' ')[0] || 'equipo')}.</h1>
        <p class="muted">Este es el pulso de la operación de hoy: rutas, paquetes en calle, entregas y alertas de inventario.</p>
        <div class="home-hero-actions">
          ${puedeOperar() ? `<button class="btn btn-primary" type="button" id="btnGenerarInicio">${ico('rayo')} Generar rutas del día</button>` : ''}
          ${puedeOperar() ? `<button class="btn btn-ghost" type="button" id="btnMovimientoInicio">${ico('inventario')} Movimiento de inventario</button>` : ''}
          ${puedeOperar() ? `<button class="btn btn-ghost" type="button" data-go="recepcion">${ico('paquete')} Recepción</button>` : ''}
          ${puedeOperar() ? `<button class="btn btn-ghost" type="button" data-go="picking">${ico('inventario')} Picking</button>` : ''}
          <button class="btn btn-ghost" type="button" data-go="rutas">${ico('rutas')} Ver reparto</button>
          <button class="btn btn-ghost" type="button" data-go="rastreo">${ico('rastreo')} Rastrear paquete</button>
        </div>
      </div>
      <div class="hero-stat">
        <strong>${numero(panel.rutas_hoy)}</strong>
        <span>rutas en el plan de hoy</span>
        <small>${numero(panel.rutas_en_ruta)} actualmente en calle</small>
      </div>
    </section>

    <div class="grid grid-kpi">
      ${kpiCard({ clase: 'blue', icono: 'rutas', etiqueta: 'Rutas de hoy', valor: numero(panel.rutas_hoy), detalle: `${numero(panel.rutas_en_ruta)} en ruta` })}
      ${kpiCard({ clase: 'green', icono: 'paquete', etiqueta: 'Bultos en ruta', valor: numero(panel.bultos_en_ruta), detalle: 'rastreo activo por guía' })}
      ${kpiCard({ clase: 'orange', icono: 'inventario', etiqueta: 'Pedidos pendientes', valor: numero(panel.pedidos_pendientes), detalle: 'listos o asignados' })}
      ${kpiCard({ clase: 'purple', icono: 'check', etiqueta: 'Entregas de hoy', valor: numero(panel.entregas_hoy), detalle: `${numero(panel.fallidas_hoy)} fallidas` })}
      ${kpiCard({ clase: 'blue', icono: 'edificio', etiqueta: 'Ocupación de bodega', valor: porcentaje(panel.ocupacion_pct), detalle: 'posiciones con existencia' })}
      ${kpiCard({ clase: 'red', icono: 'alerta', etiqueta: 'Productos bajo mínimo', valor: numero(panel.stock_bajo), detalle: 'requieren reposición' })}
      ${kpiCard({ clase: 'green', icono: 'mapa', etiqueta: 'Distancia planificada', valor: `${numero(panel.distancia_hoy_km, 1)} km`, detalle: 'circuitos de hoy' })}
      ${kpiCard({ clase: 'orange', icono: 'flota', etiqueta: 'Flota trabajando', valor: numero(panel.rutas_en_ruta), detalle: 'unidades en calle' })}
      ${kpiCard({ clase: 'orange', icono: 'inventario', etiqueta: 'Pedidos en picking', valor: numero(panel.pedidos_en_picking), detalle: `${numero(panel.tareas_picking_pendientes)} tareas pendientes` })}
      ${kpiCard({ clase: 'purple', icono: 'paquete', etiqueta: 'Pedidos en empaque', valor: numero(panel.pedidos_en_empaque), detalle: 'esperando QC' })}
      ${kpiCard({ clase: 'red', icono: 'alerta', etiqueta: 'Mermas de hoy', valor: numero(panel.mermas_hoy), detalle: 'unidades faltantes en conteos' })}
      ${kpiCard({ clase: 'blue', icono: 'reloj', etiqueta: 'Productos estancados', valor: numero(panel.productos_estancados), detalle: 'sin movimiento en 30 días' })}
    </div>

    <div class="grid grid-main section-gap">
      <section class="panel panel-pad">
        ${encabezadoPanel('Rutas recientes', 'Últimos planes generados y su estado operativo.', '<button class="panel-link" type="button" data-go="rutas">Ver todas ' + ico('flecha') + '</button>')}
        ${tablaRutas}
      </section>
      <div class="grid" style="gap:15px">
        <section class="panel panel-pad">
          ${encabezadoPanel('Pulso de la operación', 'Indicadores del turno actual.')}
          <div class="progress-list">
            <div class="progress-item">
              <div class="progress-head"><span>Entregas confirmadas</span><strong>${numero(panel.entregas_hoy)}/${numero(entregas)}</strong></div>
              <div class="progress-track"><div class="progress-fill green" style="width:${pctEntregas}%"></div></div>
            </div>
            <div class="progress-item">
              <div class="progress-head"><span>Rutas en calle</span><strong>${numero(panel.rutas_en_ruta)}/${numero(panel.rutas_hoy)}</strong></div>
              <div class="progress-track"><div class="progress-fill orange" style="width:${pctRutas}%"></div></div>
            </div>
            <div class="progress-item">
              <div class="progress-head"><span>Ocupación de bodega</span><strong>${porcentaje(panel.ocupacion_pct)}</strong></div>
              <div class="progress-track"><div class="progress-fill" style="width:${Math.min(Number(panel.ocupacion_pct) || 0, 100)}%"></div></div>
            </div>
            <div class="progress-item">
              <div class="progress-head"><span>Entregas fallidas</span><strong>${numero(panel.fallidas_hoy)}</strong></div>
              <div class="progress-track"><div class="progress-fill red" style="width:${entregas ? Math.round((panel.fallidas_hoy / entregas) * 100) : 0}%"></div></div>
            </div>
          </div>
          <div class="divider"></div>
          <div class="panel-header" style="margin-bottom:9px"><div><h2 style="font-size:13px">Productividad de picking</h2><p>Líneas surtidas hoy por operador.</p></div></div>
          ${(panel.productividad_hoy || []).length
            ? `<div class="productivity-list">${panel.productividad_hoy.map((item) => `<div class="productivity-item"><span>${esc(item.operador)}</span><strong>${numero(item.lineas)} líneas</strong><span>${numero(item.tareas)} tareas</span></div>`).join('')}</div>`
            : '<p class="tiny muted">Aún no hay tareas de picking completadas hoy.</p>'}
        </section>
        <section class="panel panel-pad">
          ${encabezadoPanel('Actividad reciente', 'Eventos de rastreo del CEDIS.', '<button class="panel-link" type="button" data-go="rastreo">Rastrear ' + ico('flecha') + '</button>')}
          ${actividad}
        </section>
      </div>
    </div>`;

  $$('[data-go]').forEach((boton) => {
    boton.addEventListener('click', () => navegar(boton.dataset.go));
  });
  $$('[data-ruta-detalle]').forEach((boton) => {
    boton.addEventListener('click', () => abrirDetalleRuta(Number(boton.dataset.rutaDetalle)));
  });
  $('#btnGenerarInicio')?.addEventListener('click', () => generarPlan(false));
  $('#btnMovimientoInicio')?.addEventListener('click', () => {
    estado.abrirMovimiento = true;
    navegar('inventario');
  });
};

/* --------------------------------------------------------------------------
   Rutas y reparto
   -------------------------------------------------------------------------- */
PAGINAS.rutas = async function (version) {
  const rutas = await api('/rutas?limite=200');
  if (!vigente(version)) return;
  estado.rutasCache = rutas;
  renderPaginaRutas(rutas);
};

function renderPaginaRutas(rutas) {
  const filtro = estado.filtroRutas;
  const visibles = filtro === 'todas' ? rutas : rutas.filter((ruta) => ruta.estado === filtro);
  const planificadas = rutas.filter((ruta) => ruta.estado === 'PLANIFICADA').length;
  const enRuta = rutas.filter((ruta) => ruta.estado === 'EN_RUTA').length;
  const completadas = rutas.filter((ruta) => ruta.estado === 'COMPLETADA').length;
  const canceladas = rutas.filter((ruta) => ruta.estado === 'CANCELADA').length;
  const bultos = rutas.reduce((total, ruta) => total + Number(ruta.num_bultos || 0), 0);
  const distancia = rutas.reduce((total, ruta) => total + Number(ruta.distancia_km || 0), 0);

  const filtros = [
    ['todas', 'Todas', rutas.length],
    ['PLANIFICADA', 'Planificadas', planificadas],
    ['EN_RUTA', 'En ruta', enRuta],
    ['COMPLETADA', 'Completadas', completadas],
    ...(canceladas ? [['CANCELADA', 'Canceladas', canceladas]] : []),
  ];
  const lista = visibles.length
    ? `<div class="route-list">${visibles.map(tarjetaRuta).join('')}</div>`
    : estadoVacio(
        'rutas',
        'Sin rutas en este filtro',
        puedeOperar()
          ? 'Genera el plan del día o cambia el filtro para ver otros estados.'
          : 'No hay rutas que coincidan con el filtro seleccionado.',
        puedeOperar() ? `<button class="btn btn-primary" type="button" data-generar-vacio>${ico('rayo')} Generar plan</button>` : '',
      );

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div>
        <p class="eyebrow">Embarques y flota</p>
        <h1>Rutas de reparto</h1>
        <p class="muted">Consolidación por zona, tipo de cliente, peso y volumen. El mapa y las paradas se cargan bajo demanda.</p>
      </div>
      <div class="page-head-actions">
        ${puedeOperar() ? `
          <button class="btn btn-ghost" type="button" id="btnReplanificarRutas">${ico('refrescar')} Replanificar</button>
          <button class="btn btn-primary" type="button" id="btnGenerarPlan">${ico('rayo')} Generar plan</button>` : ''}
        <button class="icon-button" type="button" id="btnRefrescarRutas" title="Actualizar">${ico('refrescar')}</button>
      </div>
    </div>

    <div class="route-summary">
      <span>Rutas <strong>${numero(rutas.length)}</strong></span>
      <span>Planificadas <strong>${numero(planificadas)}</strong></span>
      <span>En ruta <strong>${numero(enRuta)}</strong></span>
      <span>Completadas <strong>${numero(completadas)}</strong></span>
      <span>Bultos <strong>${numero(bultos)}</strong></span>
      <span>Distancia <strong>${numero(distancia, 1)} km</strong></span>
    </div>

    <div class="routes-toolbar">
      <div class="filter-bar">${filtros.map(([valor, etiqueta, total]) => `
        <button class="chip-filter ${filtro === valor ? 'active' : ''}" type="button" data-filtro="${valor}">${etiqueta} · ${total}</button>`).join('')}
      </div>
      <span class="tiny muted">El ahorro se calcula contra el orden natural de carga.</span>
    </div>

    ${lista}`;

  $$('[data-filtro]').forEach((boton) => {
    boton.addEventListener('click', () => {
      estado.filtroRutas = boton.dataset.filtro;
      renderPaginaRutas(estado.rutasCache);
    });
  });
  $$('[data-detalle]').forEach((boton) => {
    boton.addEventListener('click', () => abrirDetalleRuta(Number(boton.dataset.detalle)));
  });
  $$('[data-despachar]').forEach((boton) => {
    boton.addEventListener('click', () => abrirDespacho(Number(boton.dataset.despachar)));
  });
  $('#btnRefrescarRutas')?.addEventListener('click', () => renderSeccion());
  $('#btnGenerarPlan')?.addEventListener('click', () => generarPlan(false));
  $('#btnReplanificarRutas')?.addEventListener('click', () => {
    if (window.confirm('Se cancelarán las rutas PLANIFICADAS de hoy y se volverán a consolidar los pedidos. ¿Continuar?')) {
      generarPlan(true);
    }
  });
  $('[data-generar-vacio]')?.addEventListener('click', () => generarPlan(false));
}

function tarjetaRuta(ruta) {
  const puedeDespachar = ruta.estado === 'PLANIFICADA' && puedeOperar();
  return `
    <article class="panel route-card">
      <div class="route-card-head">
        <div class="route-head-left">
          <div class="route-folio">${ico('rutas')} ${esc(ruta.folio)} ${badgeZona(ruta.zona)}</div>
          <div class="route-meta">
            <span>${ico('calendario')} ${esc(fechaCorta(ruta.fecha))}</span>
            <span>${ico('flota')} ${esc(ruta.conductor.nombre)} · ${esc(ruta.vehiculo.placas)}</span>
            <span>${ico('usuarios')} ${esc(ruta.tipo_principal || 'MIXTO')}</span>
            <span>${ico('paquete')} ${plural(ruta.num_bultos, 'bulto', 'bultos')} en ${plural(ruta.num_paradas, 'parada', 'paradas')}</span>
          </div>
        </div>
        <div class="route-head-right">
          ${badgeEstado(ruta.estado)}
          ${puedeDespachar ? `<button class="btn btn-small btn-success" type="button" data-despachar="${ruta.id}">${ico('check')} Despachar</button>` : ''}
          <button class="btn btn-small btn-ghost" type="button" data-detalle="${ruta.id}">${ico('mapa')} Mapa y paradas</button>
        </div>
      </div>
      <div class="route-metrics">
        <span class="metric-chip">${ico('peso')} <strong>${peso(ruta.peso_total_kg)}</strong> / ${peso(ruta.vehiculo.capacidad_kg)}</span>
        <span class="metric-chip">${ico('paquete')} <strong>${volumen(ruta.volumen_total_m3)}</strong> / ${volumen(ruta.vehiculo.capacidad_m3)}</span>
        <span class="metric-chip">${ico('mapa')} <strong>${numero(ruta.distancia_km, 1)} km</strong> optimizados</span>
        <span class="metric-chip green">${ico('rayo')} <strong>${porcentaje(ruta.ahorro_pct)}</strong> de ahorro</span>
        <span class="metric-chip orange">${ico('reloj')} ETA <strong>${numero(ruta.eta_min, 0)} min</strong></span>
      </div>
    </article>`;
}

async function generarPlan(replanificar) {
  if (!puedeOperar()) { toast('Tu rol no puede generar rutas.', 'error'); return; }
  const botones = $$('#btnGenerarPlan, #btnGenerarInicio, #btnReplanificarRutas, [data-generar-vacio]')
    .filter((boton) => !boton.disabled);
  botones.forEach((boton) => { boton.disabled = true; });
  toast(replanificar ? 'Cancelando plan anterior y replanificando…' : 'Consolidando pedidos y calculando rutas…', 'info', 5200);
  try {
    const resultado = await api(`/rutas/generar?replanificar=${replanificar ? 'true' : 'false'}`, { method: 'POST' });
    toast(resultado.mensaje, resultado.generado ? 'success' : 'info', 6500);
    if (resultado.generado) {
      estado.filtroRutas = 'todas';
      if (estado.seccion === 'rutas') renderSeccion();
      else navegar('rutas');
    }
  } catch (error) {
    toast(error.message, 'error', 7000);
  } finally {
    botones.forEach((boton) => { boton.disabled = false; });
  }
}

/* --------------------------------------------------------------------------
   Detalle de ruta y mapa
   -------------------------------------------------------------------------- */
async function abrirDetalleRuta(rutaId) {
  try {
    const ruta = await api(`/rutas/${rutaId}`);
    mostrarDetalleRuta(ruta);
  } catch (error) {
    toast(error.message, 'error');
  }
}

function mostrarDetalleRuta(ruta) {
  const paradas = ruta.paradas || [];
  const puedeDespachar = ruta.estado === 'PLANIFICADA' && puedeOperar();
  const paradasHtml = paradas.length
    ? paradas.map((parada) => {
        const clase = parada.estado === 'ENTREGADO' ? 'done' : parada.estado === 'FALLIDO' ? 'failed' : '';
        const evidencias = parada.entrega
          ? `${parada.entrega.firma_url ? `<button class="evidence-link" type="button" data-evidencia="${esc(parada.entrega.firma_url)}" data-evidencia-titulo="Firma · ${esc(parada.cliente)}" title="Ver firma">${ico('firma')}</button>` : ''}
             ${parada.entrega.foto_url ? `<button class="evidence-link" type="button" data-evidencia="${esc(parada.entrega.foto_url)}" data-evidencia-titulo="Foto · ${esc(parada.cliente)}" title="Ver foto">${ico('camara')}</button>` : ''}`
          : '';
        const accion = parada.estado === 'PENDIENTE' && ruta.estado === 'EN_RUTA' && puedeOperar()
          ? `<button class="btn btn-small btn-success" type="button" data-entrega-parada="${parada.id}">${ico('check')} Entrega</button>`
          : '';
        const guias = (parada.bultos || []).map((bulto) => bulto.guia).join(', ');
        return `
          <div class="stop-card ${clase}">
            <span class="stop-seq">${parada.secuencia}</span>
            <div class="stop-copy">
              <strong>${esc(parada.cliente)} · ${esc(parada.pedido_folio)}</strong>
              <small title="${esc(guias)}">${esc(parada.direccion)} · ETA ${numero(parada.eta_min, 0)} min · ${plural(parada.bultos.length, 'bulto', 'bultos')}</small>
            </div>
            <div class="stop-actions">
              ${badgeEstado(parada.estado)}
              ${evidencias}
              ${accion}
            </div>
          </div>`;
      }).join('')
    : estadoVacio('mapa', 'Ruta sin paradas', 'Esta ruta no tiene pedidos asignados.');

  abrirModal({
    titulo: `Ruta ${ruta.folio}`,
    subtitulo: `${ruta.zona} · ${fechaCorta(ruta.fecha)} · ${ruta.conductor.nombre} (${ruta.vehiculo.placas})`,
    ancho: 'wide',
    cuerpo: `
      <div class="route-metrics" style="padding:0 0 15px">
        <span class="metric-chip">${ico('peso')} <strong>${peso(ruta.peso_total_kg)}</strong> / ${peso(ruta.vehiculo.capacidad_kg)}</span>
        <span class="metric-chip">${ico('paquete')} <strong>${volumen(ruta.volumen_total_m3)}</strong> / ${volumen(ruta.vehiculo.capacidad_m3)}</span>
        <span class="metric-chip">${ico('mapa')} <strong>${numero(ruta.distancia_km, 1)} km</strong> · base ${numero(ruta.distancia_base_km, 1)} km</span>
        <span class="metric-chip green">${ico('rayo')} ahorro <strong>${porcentaje(ruta.ahorro_pct)}</strong></span>
        <span class="metric-chip orange">${ico('reloj')} ETA <strong>${numero(ruta.eta_min, 0)} min</strong></span>
      </div>
      <div class="route-detail-grid">
        <div>
          <div class="route-map" id="contenedorMapa">
            <div class="route-map-loading" id="mapaCargando">Generando mapa de la ruta…</div>
            <img id="mapaRuta" alt="Mapa de la ruta ${esc(ruta.folio)}">
          </div>
        </div>
        <div class="stop-list">${paradasHtml}</div>
      </div>`,
    acciones: `
      <button class="btn btn-ghost" type="button" id="cerrarDetalle">Cerrar</button>
      <button class="btn btn-ghost" type="button" id="descargarMapa">${ico('descargar')} Descargar mapa</button>
      ${puedeDespachar ? `<button class="btn btn-success" type="button" id="despacharDesdeDetalle">${ico('check')} Validar y despachar</button>` : ''}`,
  });

  $('#cerrarDetalle').onclick = cerrarModal;
  const mapa = $('#mapaRuta');
  apiBlob(`/rutas/${ruta.id}/mapa`)
    .then((blob) => {
      mapa.src = URL.createObjectURL(blob);
      $('#mapaCargando').classList.add('hidden');
    })
    .catch((error) => {
      $('#mapaCargando').textContent = error.message;
    });
  $('#descargarMapa')?.addEventListener('click', async () => {
    try {
      const blob = await apiBlob(`/rutas/${ruta.id}/mapa`);
      await descargarBlob(blob, `ruta_${ruta.folio}.png`);
      toast('Mapa descargado.', 'success');
    } catch (error) { toast(error.message, 'error'); }
  });
  $('#despacharDesdeDetalle')?.addEventListener('click', () => abrirDespacho(ruta.id));
  $$('[data-entrega-parada]').forEach((boton) => {
    boton.addEventListener('click', () => {
      const parada = paradas.find((p) => p.id === Number(boton.dataset.entregaParada));
      if (parada) abrirEntrega(ruta, parada);
    });
  });
  $$('[data-evidencia]').forEach((boton) => {
    boton.addEventListener('click', () => verEvidencia(boton.dataset.evidencia, boton.dataset.evidenciaTitulo));
  });
}

async function verEvidencia(url, titulo) {
  try {
    const relativa = url.replace(/^\/api/, '');
    const blob = await apiBlob(relativa);
    const src = URL.createObjectURL(blob);
    abrirModal({
      titulo: titulo || 'Evidencia de entrega',
      subtitulo: 'Firma o fotografía capturada por el operador.',
      cuerpo: `<img src="${src}" alt="Evidencia de entrega" style="width:100%;border-radius:10px;border:1px solid var(--border);background:#fff">`,
      acciones: '<button class="btn btn-ghost" type="button" id="cerrarEvidencia">Cerrar</button>',
      ancho: 'narrow',
    });
    $('#cerrarEvidencia').onclick = () => { URL.revokeObjectURL(src); cerrarModal(); };
  } catch (error) {
    toast(error.message, 'error');
  }
}

/* --------------------------------------------------------------------------
   Despacho con escaneo
   -------------------------------------------------------------------------- */
async function abrirDespacho(rutaId) {
  try {
    const ruta = await api(`/rutas/${rutaId}`);
    if (ruta.estado !== 'PLANIFICADA') {
      toast(`La ruta ${ruta.folio} ya no está planificada.`, 'info');
      return;
    }
    const esperadas = (ruta.paradas || []).flatMap((parada) => parada.bultos.map((bulto) => bulto.guia));
    abrirModal({
      titulo: `Despacho · ${ruta.folio}`,
      subtitulo: `${ruta.zona} · ${ruta.conductor.nombre} · ${esperadas.length} bultos esperados`,
      cuerpo: `
        <div class="scanner-box">
          <p class="inline-note">Escanea o pega las guías de los bultos que suben a la unidad. El sistema rechaza el despacho si falta una guía o si se escanea mercancía de otra ruta.</p>
          <div class="scanner-expected" id="guiasEsperadas">${esperadas.map((guia) => `<code data-guia="${esc(guia)}">${esc(guia)}</code>`).join('')}</div>
          <label class="field" style="margin:4px 0 0">
            <span>Guías escaneadas</span>
            <textarea class="textarea" id="scanInput" placeholder="LX-00011&#10;LX-00012&#10;LX-00013"></textarea>
          </label>
          <div class="scan-result" id="scanResult"></div>
        </div>`,
      acciones: `
        <button class="btn btn-ghost" type="button" id="cancelarDespacho">Cancelar</button>
        <button class="btn btn-ghost" type="button" id="cargarTodas">${ico('paquete')} Simular escaneo completo</button>
        <button class="btn btn-success" type="button" id="confirmarDespacho">${ico('check')} Validar y despachar</button>`,
    });
    $('#cancelarDespacho').onclick = cerrarModal;
    $('#cargarTodas').onclick = () => {
      $('#scanInput').value = esperadas.join('\n');
      $('#scanInput').focus();
    };
    $('#confirmarDespacho').onclick = async () => {
      const boton = $('#confirmarDespacho');
      const restaurar = bloquear(boton, 'Validando…');
      const guias = $('#scanInput').value.split(/[\s,;]+/).map((g) => g.trim()).filter(Boolean);
      const resultado = $('#scanResult');
      resultado.className = 'scan-result';
      resultado.textContent = '';
      if (!guias.length) {
        resultado.classList.add('error');
        resultado.textContent = 'Escanea al menos una guía antes de continuar.';
        restaurar();
        return;
      }
      try {
        const respuesta = await api(`/rutas/${ruta.id}/despachar`, {
          method: 'POST',
          body: JSON.stringify({ guias }),
        });
        toast(respuesta.mensaje, 'success', 6000);
        cerrarModal();
        renderSeccion();
      } catch (error) {
        resultado.classList.add('error');
        const datos = error.datos || {};
        if (datos.faltantes?.length || datos.ajenas?.length) {
          const faltantes = datos.faltantes || [];
          const ajenas = datos.ajenas || [];
          resultado.innerHTML = [
            faltantes.length ? `<div>Faltan: <span class="mono">${faltantes.map(esc).join(', ')}</span></div>` : '',
            ajenas.length ? `<div>No pertenecen a la ruta: <span class="mono">${ajenas.map(esc).join(', ')}</span></div>` : '',
          ].join('');
          const escaneadas = new Set(guias.map((g) => g.toUpperCase()));
          $$('#guiasEsperadas code').forEach((code) => {
            code.classList.toggle('ok', escaneadas.has(code.dataset.guia.toUpperCase()));
          });
        } else {
          resultado.textContent = error.message;
        }
        toast(error.message, 'error', 6500);
        restaurar();
      }
    };
  } catch (error) {
    toast(error.message, 'error');
  }
}

/* --------------------------------------------------------------------------
   Registro de entrega con firma y foto
   -------------------------------------------------------------------------- */
function abrirEntrega(ruta, parada) {
  const cuerpo = `
    <form id="formEntrega" novalidate>
      <div class="detail-block">
        <h3>Parada ${parada.secuencia} · ${esc(parada.cliente)}</h3>
        <p class="inline-note">${esc(parada.direccion)} · Pedido ${esc(parada.pedido_folio)} · ${plural(parada.bultos.length, 'bulto', 'bultos')}</p>
      </div>
      <div class="detail-block">
        <h3>Resultado de la entrega</h3>
        <div class="radio-row">
          <label class="radio-card">
            <input type="radio" name="resultado" value="ENTREGADO" checked>
            <span>${ico('check')} Entregado</span>
          </label>
          <label class="radio-card">
            <input type="radio" name="resultado" value="FALLIDO">
            <span>${ico('alerta')} Entrega fallida</span>
          </label>
        </div>
      </div>

      <div class="conditional visible" id="bloqueEntregado">
        <div class="form-grid">
          <label class="field span-2">
            <span>Nombre de quien recibió *</span>
            <input class="input" id="recibioNombre" maxlength="150" placeholder="Ej. Sofía Treviño">
          </label>
          <div class="field span-2">
            <span>Firma del cliente *</span>
            <div class="signature-wrap"><canvas id="firmaCanvas" aria-label="Firma del cliente"></canvas></div>
            <div class="signature-help"><span>Firma con el mouse o con el dedo en la tableta.</span><button class="btn-link" type="button" id="limpiarFirma">Limpiar firma</button></div>
          </div>
          <label class="field span-2">
            <span>Fotografía de la mercancía</span>
            <span class="file-drop">${ico('camara')} Tomar o seleccionar foto<input type="file" id="fotoEntrega" accept="image/png,image/jpeg"></span>
            <img class="preview-thumb" id="fotoPreview" alt="Vista previa de la foto" hidden>
          </label>
        </div>
      </div>

      <div class="conditional" id="bloqueFallido">
        <div class="form-grid">
          <label class="field">
            <span>Motivo de la falla *</span>
            <select class="select" id="motivoFallo">
              <option value="CLIENTE_CERRADO">Cliente cerrado</option>
              <option value="DIRECCION_INCORRECTA">Dirección incorrecta</option>
              <option value="RECHAZO">Rechazo de la mercancía</option>
              <option value="OTRO">Otro motivo</option>
            </select>
          </label>
          <label class="field">
            <span>Reprogramar para</span>
            <input class="input" type="date" id="reprogramadoPara" min="${hoyISO()}" value="${mananaISO()}">
          </label>
        </div>
      </div>

      <label class="field" style="margin-top:13px">
        <span>Comentario del operador</span>
        <textarea class="textarea" id="comentarioEntrega" maxlength="1000" placeholder="Detalles de la entrega, persona que atendió o motivo de la falla…"></textarea>
      </label>
      <p class="form-error" id="errorEntrega" role="alert"></p>
    </form>`;

  abrirModal({
    titulo: `Registrar entrega · ${ruta.folio}`,
    subtitulo: `Parada ${parada.secuencia} de ${ruta.num_paradas} · ${parada.cliente}`,
    cuerpo,
    acciones: `
      <button class="btn btn-ghost" type="button" id="cancelarEntrega">Cancelar</button>
      <button class="btn btn-success" type="button" id="guardarEntrega">${ico('check')} Guardar evidencia</button>`,
    ancho: '',
  });

  const firma = inicializarFirma($('#firmaCanvas'));
  const alternar = () => {
    const fallido = $('input[name="resultado"]:checked').value === 'FALLIDO';
    $('#bloqueEntregado').classList.toggle('visible', !fallido);
    $('#bloqueFallido').classList.toggle('visible', fallido);
  };
  $$('input[name="resultado"]').forEach((radio) => radio.addEventListener('change', alternar));
  $('#limpiarFirma').onclick = () => firma.limpiar();
  $('#fotoEntrega').addEventListener('change', (evento) => {
    const archivo = evento.target.files?.[0];
    if (!archivo) return;
    const lector = new FileReader();
    lector.onload = () => {
      const preview = $('#fotoPreview');
      preview.src = lector.result;
      preview.hidden = false;
    };
    lector.readAsDataURL(archivo);
  });
  $('#cancelarEntrega').onclick = () => mostrarDetalleRuta(ruta);
  $('#guardarEntrega').onclick = async () => {
    const boton = $('#guardarEntrega');
    const errorBox = $('#errorEntrega');
    errorBox.textContent = '';
    const resultado = $('input[name="resultado"]:checked').value;
    const recibio = $('#recibioNombre').value.trim();
    const motivo = $('#motivoFallo').value;
    const comentario = $('#comentarioEntrega').value.trim();
    const reprogramado = $('#reprogramadoPara').value || null;
    const fotoInput = $('#fotoEntrega');
    let fotoBase64 = null;

    if (resultado === 'ENTREGADO') {
      if (!recibio) { errorBox.textContent = 'Registra el nombre de quien recibió la mercancía.'; return; }
      if (!firma.hayFirma()) { errorBox.textContent = 'La firma del cliente es obligatoria.'; return; }
    }

    if (fotoInput.files?.[0]) {
      fotoBase64 = await leerArchivoBase64(fotoInput.files[0]);
    }
    const restaurar = bloquear(boton, 'Guardando…');
    try {
      const respuesta = await api(`/rutas/${ruta.id}/paradas/${parada.id}/entrega`, {
        method: 'POST',
        body: JSON.stringify({
          resultado,
          recibio_nombre: resultado === 'ENTREGADO' ? recibio : null,
          firma_base64: resultado === 'ENTREGADO' ? firma.dataUrl() : null,
          foto_base64: fotoBase64,
          motivo_fallo: resultado === 'FALLIDO' ? motivo : null,
          comentario: comentario || null,
          reprogramado_para: resultado === 'FALLIDO' ? reprogramado : null,
        }),
      });
      toast(respuesta.mensaje, 'success', 5000);
      mostrarDetalleRuta(respuesta.ruta);
    } catch (error) {
      errorBox.textContent = error.message;
      toast(error.message, 'error', 6500);
      restaurar();
    }
  };
}

function leerArchivoBase64(archivo) {
  return new Promise((resolver, rechazar) => {
    const lector = new FileReader();
    lector.onload = () => resolver(lector.result);
    lector.onerror = () => rechazar(new Error('No se pudo leer la fotografía.'));
    lector.readAsDataURL(archivo);
  });
}

function inicializarFirma(canvas) {
  const ctx = canvas.getContext('2d');
  const alto = 170;
  const dpr = window.devicePixelRatio || 1;
  const anchoCss = canvas.getBoundingClientRect().width || 520;
  canvas.width = Math.round(anchoCss * dpr);
  canvas.height = Math.round(alto * dpr);
  canvas.style.height = `${alto}px`;
  ctx.scale(dpr, dpr);
  ctx.lineWidth = 2.2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = '#12263c';
  let dibujando = false;
  let hay = false;

  const punto = (evento) => {
    const rect = canvas.getBoundingClientRect();
    return { x: evento.clientX - rect.left, y: evento.clientY - rect.top };
  };

  canvas.addEventListener('pointerdown', (evento) => {
    dibujando = true;
    canvas.setPointerCapture?.(evento.pointerId);
    const p = punto(evento);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  });
  canvas.addEventListener('pointermove', (evento) => {
    if (!dibujando) return;
    const p = punto(evento);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    hay = true;
  });
  const terminar = () => { dibujando = false; };
  canvas.addEventListener('pointerup', terminar);
  canvas.addEventListener('pointercancel', terminar);
  canvas.addEventListener('pointerleave', terminar);

  return {
    hayFirma: () => hay,
    dataUrl: () => canvas.toDataURL('image/png'),
    limpiar: () => {
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.restore();
      hay = false;
    },
  };
}

/* --------------------------------------------------------------------------
   Rastreo de paquetes
   -------------------------------------------------------------------------- */
PAGINAS.rastreo = async function (version) {
  const recientes = await api('/rastreo?limite=8');
  if (!vigente(version)) return;
  let resultado = null;
  let error = '';
  if (estado.rastreoGuia) {
    try {
      resultado = await api(`/rastreo/${encodeURIComponent(estado.rastreoGuia)}`);
    } catch (fallo) {
      error = fallo.message;
    }
  }
  if (!vigente(version)) return;
  renderPaginaRastreo(recientes, resultado, error);
};

function renderPaginaRastreo(recientes, resultado, error) {
  const ejemplos = (recientes || []).slice(0, 6);
  const tablaRecientes = (recientes || []).length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Guía</th><th>Cliente</th><th>Pedido</th><th>Último estado</th><th>Actualizado</th><th></th></tr></thead>
        <tbody>${recientes.map((item) => `
          <tr>
            <td class="primary-cell mono">${esc(item.guia)}</td>
            <td>${esc(item.cliente)}</td>
            <td>${esc(item.pedido_folio)}</td>
            <td>${badgeEstado(item.estado)}</td>
            <td>${esc(fechaHora(item.fecha))}</td>
            <td class="text-right"><button class="btn btn-small btn-ghost" type="button" data-guia="${esc(item.guia)}">Rastrear</button></td>
          </tr>`).join('')}
        </tbody></table></div>`
    : estadoVacio('rastreo', 'Sin paquetes recientes', 'Cuando se etiquete o mueva un bulto aparecerá aquí.');

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div>
        <p class="eyebrow">Trazabilidad</p>
        <h1>Rastreo de paquetes</h1>
        <p class="muted">Consulta la línea de tiempo completa de una guía: recepción, asignación, salida, entrega o intento fallido.</p>
      </div>
      <span class="page-date">${ico('calendario')} ${esc(fechaLarga())}</span>
    </div>

    <section class="panel panel-pad">
      <form class="tracking-search" id="formRastreo">
        <input class="input" id="guiaInput" value="${esc(estado.rastreoGuia)}" placeholder="Ej. LX-00011" autocomplete="off" aria-label="Número de guía">
        <button class="btn btn-primary" type="submit">${ico('rastreo')} Rastrear</button>
      </form>
      <div class="chip-examples"><span>Ejemplos:</span>${ejemplos.map((item) => `<button class="guide-chip" type="button" data-guia="${esc(item.guia)}">${esc(item.guia)}</button>`).join('')}</div>
    </section>

    ${resultado ? bloqueRastreo(resultado) : error
      ? `<section class="panel panel-pad section-gap">${estadoVacio('alerta', 'Guía no encontrada', error)}</section>`
      : `<section class="panel panel-pad section-gap">${estadoVacio('rastreo', 'Busca una guía para empezar', 'Puedes escribir el número de guía o elegir uno de los ejemplos recientes.')}</section>`}

    <section class="panel panel-pad section-gap">
      ${encabezadoPanel('Últimos paquetes con movimiento', 'Guías actualizadas recientemente en el CEDIS.')}
      ${tablaRecientes}
    </section>`;

  $('#formRastreo').addEventListener('submit', (evento) => {
    evento.preventDefault();
    irARastreo($('#guiaInput').value);
  });
  $$('[data-guia]').forEach((boton) => {
    boton.addEventListener('click', () => irARastreo(boton.dataset.guia));
  });
  $('#copiarGuia')?.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(resultado.guia);
      toast('Guía copiada al portapapeles.', 'success');
    } catch {
      toast(`Guía: ${resultado.guia}`, 'info');
    }
  });
}

function bloqueRastreo(paquete) {
  const eventos = paquete.eventos || [];
  const timeline = eventos.length
    ? `<div class="timeline">${eventos.map((evento, indice) => {
        const clase = evento.estado === 'ENTREGADO' ? 'ok'
          : ['FALLIDO'].includes(evento.estado) ? 'bad'
          : ['REPROGRAMADO', 'DEVUELTO'].includes(evento.estado) ? 'warn' : 'info';
        return `<div class="timeline-item ${clase}">
          <span class="timeline-dot"></span>
          <div class="timeline-copy">
            <strong>${esc(evento.estado)}${indice === 0 ? ' · último movimiento' : ''}</strong>
            <p>${esc(evento.descripcion)}</p>
            <small>${esc(fechaHora(evento.fecha))} · ${esc(evento.ubicacion || 'CEDIS')}${evento.usuario ? ` · ${esc(evento.usuario)}` : ''}</small>
          </div>
        </div>`;
      }).join('')}</div>`
    : estadoVacio('reloj', 'Sin eventos', 'Esta guía aún no tiene movimientos registrados.');

  return `<section class="panel panel-pad tracking-result">
    <div class="tracking-head">
      <div>
        <div class="eyebrow">Guía de rastreo</div>
        <div class="tracking-guide">${esc(paquete.guia)}</div>
        <div class="tracking-sub">${esc(paquete.descripcion)} · ${esc(paquete.cliente)}</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        ${badgeEstado(paquete.estado)}
        <button class="btn btn-small btn-ghost" type="button" id="copiarGuia">${ico('paquete')} Copiar guía</button>
      </div>
    </div>
    <div class="tracking-grid">
      <div class="panel panel-pad">
        <div class="info-grid">
          <div class="info-item"><span>Cliente</span><strong>${esc(paquete.cliente)}</strong></div>
          <div class="info-item"><span>Tipo de cliente</span><strong>${esc(paquete.tipo_cliente)}</strong></div>
          <div class="info-item"><span>Pedido</span><strong>${esc(paquete.pedido_folio)}</strong></div>
          <div class="info-item"><span>Estado del pedido</span><strong>${esc(paquete.pedido_estado)}</strong></div>
          <div class="info-item"><span>Zona</span><strong>${esc(paquete.zona)}</strong></div>
          <div class="info-item"><span>Ruta</span><strong>${esc(paquete.ruta_folio || 'Sin asignar')}</strong></div>
          <div class="info-item"><span>Peso</span><strong>${peso(paquete.peso_kg)}</strong></div>
          <div class="info-item"><span>Volumen</span><strong>${volumen(paquete.volumen_m3)}</strong></div>
          <div class="info-item" style="grid-column:1/-1"><span>Dirección</span><strong>${esc(paquete.direccion)}</strong></div>
          <div class="info-item"><span>Teléfono</span><strong>${esc(paquete.telefono || '—')}</strong></div>
          <div class="info-item"><span>Compromiso</span><strong>${esc(fechaCorta(paquete.fecha_compromiso))}</strong></div>
        </div>
      </div>
      <div class="panel panel-pad">
        <div class="panel-header"><div><h2>Línea de tiempo</h2><p>Eventos registrados para esta guía.</p></div></div>
        ${timeline}
      </div>
    </div>
  </section>`;
}

/* --------------------------------------------------------------------------
   Flota
   -------------------------------------------------------------------------- */
PAGINAS.flota = async function (version) {
  const flota = await api('/flota');
  if (!vigente(version)) return;
  const vehiculos = flota.vehiculos || [];
  const conductores = flota.conductores || [];
  const historial = flota.historial || [];
  const capacidadTotal = vehiculos.reduce((total, vehiculo) => total + Number(vehiculo.capacidad_kg || 0), 0);

  const tarjetasVehiculo = vehiculos.length
    ? `<div class="grid grid-3">${vehiculos.map((vehiculo) => `
        <article class="panel panel-pad">
          <div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start">
            <div><div class="route-folio">${ico('flota')} ${esc(vehiculo.placas)}</div><div class="tiny muted">${esc(vehiculo.modelo)}</div></div>
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:flex-end">
              ${vehiculo.activo ? '<span class="badge completada">Activa</span>' : '<span class="badge cancelada">Inactiva</span>'}
              ${esAdmin() ? `<button class="btn btn-small btn-ghost" type="button" data-editar-vehiculo="${vehiculo.id}">Editar</button>` : ''}
            </div>
          </div>
          <div class="route-metrics" style="padding:14px 0 0">
            <span class="metric-chip">${ico('peso')} <strong>${peso(vehiculo.capacidad_kg)}</strong></span>
            <span class="metric-chip">${ico('paquete')} <strong>${volumen(vehiculo.capacidad_m3)}</strong></span>
          </div>
        </article>`).join('')}</div>`
    : estadoVacio('flota', 'Sin vehículos registrados', 'Agrega una unidad para comenzar a planificar rutas.');

  const tablaConductores = conductores.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Conductor</th><th>Licencia</th><th>Teléfono</th><th>Estado</th><th></th></tr></thead>
        <tbody>${conductores.map((conductor) => `
          <tr><td class="primary-cell">${esc(conductor.nombre)}</td><td class="mono">${esc(conductor.licencia)}</td><td>${esc(conductor.telefono || '—')}</td><td>${conductor.activo ? '<span class="badge completada">Activo</span>' : '<span class="badge cancelada">Inactivo</span>'}</td><td class="text-right">${esAdmin() ? `<button class="btn btn-small btn-ghost" type="button" data-editar-conductor="${conductor.id}">Editar</button>` : ''}</td></tr>`).join('')}
        </tbody></table></div>`
    : estadoVacio('usuarios', 'Sin conductores', 'Registra al personal que operará las unidades.');

  const tablaHistorial = historial.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Ruta</th><th>Fecha</th><th>Zona</th><th>Unidad</th><th>Conductor</th><th>Distancia</th><th>Estado</th><th></th></tr></thead>
        <tbody>${historial.map((ruta) => `
          <tr><td class="primary-cell">${esc(ruta.folio)}</td><td>${esc(fechaCorta(ruta.fecha))}</td><td>${badgeZona(ruta.zona)}</td><td>${esc(ruta.vehiculo.placas)}</td><td>${esc(ruta.conductor.nombre)}</td><td>${numero(ruta.distancia_km, 1)} km</td><td>${badgeEstado(ruta.estado)}</td><td class="text-right"><button class="btn btn-small btn-ghost" type="button" data-ruta-detalle="${ruta.id}">Ver</button></td></tr>`).join('')}
        </tbody></table></div>`
    : estadoVacio('rutas', 'Sin historial de rutas', 'Las rutas completadas aparecerán en este historial.');

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div><p class="eyebrow">Control de flota</p><h1>Flota y conductores</h1><p class="muted">Capacidad de carga, unidades activas e historial de rutas de reparto.</p></div>
      ${esAdmin() ? `<div class="page-head-actions"><button class="btn btn-ghost" type="button" id="nuevoConductor">${ico('usuarios')} Nuevo conductor</button><button class="btn btn-primary" type="button" id="nuevoVehiculo">${ico('mas')} Nuevo vehículo</button></div>` : ''}
    </div>
    <div class="grid grid-kpi">
      ${kpiCard({ clase: 'blue', icono: 'flota', etiqueta: 'Unidades activas', valor: numero(vehiculos.filter((v) => v.activo).length), detalle: `${numero(vehiculos.length)} registradas` })}
      ${kpiCard({ clase: 'green', icono: 'peso', etiqueta: 'Capacidad total', valor: peso(capacidadTotal), detalle: 'suma de la flota' })}
      ${kpiCard({ clase: 'purple', icono: 'usuarios', etiqueta: 'Conductores', valor: numero(conductores.filter((c) => c.activo).length), detalle: 'activos para asignación' })}
      ${kpiCard({ clase: 'orange', icono: 'rutas', etiqueta: 'Rutas históricas', valor: numero(historial.length), detalle: 'últimos planes' })}
    </div>
    <div class="section-gap">${tarjetasVehiculo}</div>
    <div class="grid grid-2 section-gap">
      <section class="panel panel-pad">${encabezadoPanel('Conductores', 'Personal habilitado para operar unidades.')}${tablaConductores}</section>
      <section class="panel panel-pad">${encabezadoPanel('Historial de rutas', 'Planes recientes y su estado.')}${tablaHistorial}</section>
    </div>`;

  $$('[data-ruta-detalle]').forEach((boton) => boton.addEventListener('click', () => abrirDetalleRuta(Number(boton.dataset.rutaDetalle))));
  $$('[data-editar-vehiculo]').forEach((boton) => boton.addEventListener('click', () => {
    const vehiculo = vehiculos.find((item) => item.id === Number(boton.dataset.editarVehiculo));
    if (vehiculo) abrirEditarVehiculo(vehiculo);
  }));
  $$('[data-editar-conductor]').forEach((boton) => boton.addEventListener('click', () => {
    const conductor = conductores.find((item) => item.id === Number(boton.dataset.editarConductor));
    if (conductor) abrirEditarConductor(conductor);
  }));
  $('#nuevoVehiculo')?.addEventListener('click', abrirNuevoVehiculo);
  $('#nuevoConductor')?.addEventListener('click', abrirNuevoConductor);
};

function abrirNuevoVehiculo() {
  abrirModal({
    titulo: 'Registrar vehículo',
    subtitulo: 'Agrega una unidad a la flota del CEDIS.',
    cuerpo: `<form id="formVehiculo"><div class="form-grid">
      <label class="field"><span>Placas *</span><input class="input" id="vehPlacas" maxlength="20" placeholder="LX-4821" required></label>
      <label class="field"><span>Modelo *</span><input class="input" id="vehModelo" maxlength="80" placeholder="Nissan NP300 · caja seca" required></label>
      <label class="field"><span>Capacidad de peso (kg) *</span><input class="input" id="vehPeso" type="number" min="1" step="0.01" placeholder="1200" required></label>
      <label class="field"><span>Capacidad cúbica (m³) *</span><input class="input" id="vehVolumen" type="number" min="0.01" step="0.001" placeholder="8" required></label>
    </div><p class="form-error" id="errorVehiculo"></p></form>`,
    acciones: '<button class="btn btn-ghost" type="button" id="cancelarVehiculo">Cancelar</button><button class="btn btn-primary" type="button" id="guardarVehiculo">Guardar vehículo</button>',
  });
  $('#cancelarVehiculo').onclick = cerrarModal;
  $('#guardarVehiculo').onclick = async () => {
    const boton = $('#guardarVehiculo');
    const restaurar = bloquear(boton, 'Guardando…');
    try {
      await api('/flota/vehiculos', { method: 'POST', body: JSON.stringify({
        placas: $('#vehPlacas').value.trim(), modelo: $('#vehModelo').value.trim(),
        capacidad_kg: Number($('#vehPeso').value), capacidad_m3: Number($('#vehVolumen').value),
      }) });
      toast('Vehículo registrado.', 'success'); cerrarModal(); renderSeccion();
    } catch (error) { $('#errorVehiculo').textContent = error.message; toast(error.message, 'error'); restaurar(); }
  };
}

function abrirEditarVehiculo(vehiculo) {
  abrirModal({
    titulo: `Editar ${vehiculo.placas}`,
    subtitulo: 'Actualiza capacidad o desactiva la unidad sin borrar su historial.',
    cuerpo: `<form id="formEditarVehiculo"><div class="form-grid">
      <label class="field span-2"><span>Modelo *</span><input class="input" id="eveModelo" maxlength="80" value="${esc(vehiculo.modelo)}" required></label>
      <label class="field"><span>Capacidad de peso (kg) *</span><input class="input" id="evePeso" type="number" min="0.01" step="0.01" value="${vehiculo.capacidad_kg}" required></label>
      <label class="field"><span>Capacidad cúbica (m³) *</span><input class="input" id="eveVolumen" type="number" min="0.001" step="0.001" value="${vehiculo.capacidad_m3}" required></label>
      <label class="check-row span-2"><input type="checkbox" id="eveActivo" ${vehiculo.activo ? 'checked' : ''}><span>Vehículo activo para planificación</span></label>
    </div><p class="form-error" id="errorEditarVehiculo"></p></form>`,
    acciones: '<button class="btn btn-ghost" type="button" id="cancelarEditarVehiculo">Cancelar</button><button class="btn btn-primary" type="button" id="guardarEditarVehiculo">Guardar cambios</button>',
  });
  $('#cancelarEditarVehiculo').onclick = cerrarModal;
  $('#guardarEditarVehiculo').onclick = async () => {
    const boton = $('#guardarEditarVehiculo');
    const restaurar = bloquear(boton, 'Guardando…');
    try {
      await api(`/flota/vehiculos/${vehiculo.id}`, { method: 'PATCH', body: JSON.stringify({
        modelo: $('#eveModelo').value.trim(), capacidad_kg: Number($('#evePeso').value),
        capacidad_m3: Number($('#eveVolumen').value), activo: $('#eveActivo').checked,
      }) });
      toast('Vehículo actualizado.', 'success'); cerrarModal(); renderSeccion();
    } catch (error) { $('#errorEditarVehiculo').textContent = error.message; toast(error.message, 'error'); restaurar(); }
  };
}

function abrirEditarConductor(conductor) {
  abrirModal({
    titulo: `Editar ${conductor.nombre}`,
    subtitulo: 'Actualiza los datos del conductor o desactívalo sin borrar su historial.',
    cuerpo: `<form id="formEditarConductor"><div class="form-grid">
      <label class="field span-2"><span>Nombre completo *</span><input class="input" id="ecoNombre" maxlength="120" value="${esc(conductor.nombre)}" required></label>
      <label class="field"><span>Teléfono</span><input class="input" id="ecoTelefono" maxlength="30" value="${esc(conductor.telefono || '')}"></label>
      <label class="field"><span>Licencia *</span><input class="input" id="ecoLicencia" maxlength="40" value="${esc(conductor.licencia)}" required></label>
      <label class="check-row span-2"><input type="checkbox" id="ecoActivo" ${conductor.activo ? 'checked' : ''}><span>Conductor activo para asignación</span></label>
    </div><p class="form-error" id="errorEditarConductor"></p></form>`,
    acciones: '<button class="btn btn-ghost" type="button" id="cancelarEditarConductor">Cancelar</button><button class="btn btn-primary" type="button" id="guardarEditarConductor">Guardar cambios</button>',
  });
  $('#cancelarEditarConductor').onclick = cerrarModal;
  $('#guardarEditarConductor').onclick = async () => {
    const boton = $('#guardarEditarConductor');
    const restaurar = bloquear(boton, 'Guardando…');
    try {
      await api(`/flota/conductores/${conductor.id}`, { method: 'PATCH', body: JSON.stringify({
        nombre: $('#ecoNombre').value.trim(), telefono: $('#ecoTelefono').value.trim() || null,
        licencia: $('#ecoLicencia').value.trim(), activo: $('#ecoActivo').checked,
      }) });
      toast('Conductor actualizado.', 'success'); cerrarModal(); renderSeccion();
    } catch (error) { $('#errorEditarConductor').textContent = error.message; toast(error.message, 'error'); restaurar(); }
  };
}

function abrirNuevoConductor() {
  abrirModal({
    titulo: 'Registrar conductor',
    subtitulo: 'Agrega al personal que operará las rutas.',
    cuerpo: `<form id="formConductor"><div class="form-grid">
      <label class="field span-2"><span>Nombre completo *</span><input class="input" id="conNombre" maxlength="120" placeholder="R. Aguilar" required></label>
      <label class="field"><span>Teléfono</span><input class="input" id="conTelefono" maxlength="30" placeholder="81 2100 3301"></label>
      <label class="field"><span>Licencia *</span><input class="input" id="conLicencia" maxlength="40" placeholder="LIC-AGU-8812" required></label>
    </div><p class="form-error" id="errorConductor"></p></form>`,
    acciones: '<button class="btn btn-ghost" type="button" id="cancelarConductor">Cancelar</button><button class="btn btn-primary" type="button" id="guardarConductor">Guardar conductor</button>',
  });
  $('#cancelarConductor').onclick = cerrarModal;
  $('#guardarConductor').onclick = async () => {
    const boton = $('#guardarConductor');
    const restaurar = bloquear(boton, 'Guardando…');
    try {
      await api('/flota/conductores', { method: 'POST', body: JSON.stringify({
        nombre: $('#conNombre').value.trim(), telefono: $('#conTelefono').value.trim() || null, licencia: $('#conLicencia').value.trim(),
      }) });
      toast('Conductor registrado.', 'success'); cerrarModal(); renderSeccion();
    } catch (error) { $('#errorConductor').textContent = error.message; toast(error.message, 'error'); restaurar(); }
  };
}

/* --------------------------------------------------------------------------
   Inventario
   -------------------------------------------------------------------------- */
PAGINAS.inventario = async function (version) {
  const [stock, movimientos, traslados] = await Promise.all([
    api('/inventario/stock'),
    api('/inventario/movimientos?limite=80'),
    api('/inventario/traslados?limite=40'),
  ]);
  if (!vigente(version)) return;
  const totalUnidades = stock.reduce((total, item) => total + Number(item.stock_total || 0), 0);
  const bajoMinimo = stock.filter((item) => item.bajo_minimo).length;
  const ubicaciones = stock.reduce((total, item) => total + Number(item.numero_ubicaciones || 0), 0);

  const filasStock = stock.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Producto</th><th>SKU</th><th>Existencia</th><th>Mínimo</th><th>Ubicaciones</th><th>Vence</th><th>Estado</th></tr></thead>
        <tbody>${stock.map((item) => {
          const objetivo = Math.max(Number(item.stock_minimo) * 3, 1);
          const pct = Math.min(100, Math.round((Number(item.stock_total) / objetivo) * 100));
          return `<tr>
            <td class="primary-cell">${esc(item.nombre)}</td>
            <td class="mono">${esc(item.sku)}</td>
            <td><div class="stock-bar"><span>${numero(item.stock_total)}</span><div class="stock-track"><div class="stock-fill ${item.bajo_minimo ? 'low' : ''}" style="width:${pct}%"></div></div></div></td>
            <td>${numero(item.stock_minimo)}</td>
            <td>${numero(item.numero_ubicaciones)}</td>
            <td>${esc(fechaCorta(item.proximo_vencimiento))}</td>
            <td>${item.bajo_minimo ? '<span class="badge badge-low">Bajo mínimo</span>' : '<span class="badge completada">Disponible</span>'}</td>
          </tr>`;
        }).join('')}
        </tbody></table></div>`
    : estadoVacio('inventario', 'Sin productos', 'Registra productos y ubicaciones para operar el almacén.');

  const filasMovimientos = movimientos.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Fecha</th><th>Producto</th><th>Ubicación</th><th>Tipo</th><th>Cantidad</th><th>Usuario</th></tr></thead>
        <tbody>${movimientos.map((movimiento) => `
          <tr><td>${esc(fechaHora(movimiento.fecha))}</td><td class="primary-cell">${esc(movimiento.producto)}<span class="sub">${esc(movimiento.sku)}</span></td><td class="mono">${esc(movimiento.ubicacion)}</td><td><span class="badge ${movimiento.tipo === 'ENTRADA' ? 'entregado' : 'en-ruta'}">${esc(movimiento.tipo)}</span></td><td>${numero(movimiento.cantidad)}</td><td>${esc(movimiento.usuario || '—')}</td></tr>`).join('')}
        </tbody></table></div>`
    : estadoVacio('inventario', 'Sin movimientos', 'Los movimientos de entrada y salida aparecerán aquí.');

  const filasTraslados = traslados.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Fecha</th><th>Producto</th><th>Cantidad</th><th>Origen → destino</th><th>Usuario</th><th>Comentario</th></tr></thead>
        <tbody>${traslados.map((traslado) => `<tr>
          <td class="nowrap">${esc(fechaHora(traslado.fecha))}</td><td class="primary-cell">${esc(traslado.producto)}</td>
          <td>${numero(traslado.cantidad)}</td><td class="mono">${esc(traslado.origen)} → ${esc(traslado.destino)}</td>
          <td>${esc(traslado.usuario || '—')}</td><td class="tiny muted">${esc(traslado.comentario || '—')}</td>
        </tr>`).join('')}</tbody></table></div>`
    : estadoVacio('inventario', 'Sin traslados', 'Los movimientos entre posiciones aparecerán aquí.');

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div><p class="eyebrow">Almacén</p><h1>Inventario en tiempo real</h1><p class="muted">Existencias por producto, mínimos, ubicaciones y últimos movimientos del CEDIS.</p></div>
      ${puedeOperar() ? `<div class="page-head-actions"><button class="btn btn-ghost" type="button" id="nuevoTraslado">${ico('flecha')} Traslado interno</button><button class="btn btn-primary" type="button" id="nuevoMovimiento">${ico('mas')} Registrar movimiento</button></div>` : ''}
    </div>
    <div class="grid grid-kpi">
      ${kpiCard({ clase: 'blue', icono: 'inventario', etiqueta: 'Unidades en stock', valor: numero(totalUnidades), detalle: 'suma de existencias' })}
      ${kpiCard({ clase: 'green', icono: 'edificio', etiqueta: 'SKUs activos', valor: numero(stock.length), detalle: `${numero(ubicaciones)} posiciones ocupadas` })}
      ${kpiCard({ clase: 'red', icono: 'alerta', etiqueta: 'Bajo mínimo', valor: numero(bajoMinimo), detalle: 'requieren reposición' })}
      ${kpiCard({ clase: 'orange', icono: 'paquete', etiqueta: 'Movimientos recientes', valor: numero(movimientos.length), detalle: 'últimos 80 registros' })}
    </div>
    <section class="panel panel-pad section-gap">${encabezadoPanel('Existencias por producto', 'La barra compara la existencia contra el mínimo de reposición.')}${filasStock}</section>
    <section class="panel panel-pad section-gap">${encabezadoPanel('Movimientos de almacén', 'Entradas y salidas registradas por el equipo.')}${filasMovimientos}</section>
    <section class="panel panel-pad section-gap">${encabezadoPanel('Traslados internos', 'Reubicaciones entre posiciones y zonas del almacén.')}${filasTraslados}</section>`;

  $('#nuevoMovimiento')?.addEventListener('click', abrirMovimientoInventario);
  $('#nuevoTraslado')?.addEventListener('click', abrirTrasladoInventario);
  if (estado.abrirMovimiento) {
    estado.abrirMovimiento = false;
    abrirMovimientoInventario();
  }
};

async function abrirTrasladoInventario() {
  try {
    const catalogo = await api('/inventario/catalogo');
    const opcionesUbicacion = catalogo.ubicaciones
      .map((ubicacion) => `<option value="${ubicacion.id}">${esc(ubicacion.codigo)} · ${esc(ubicacion.tipo_zona)}</option>`)
      .join('');
    abrirModal({
      titulo: 'Traslado interno de mercancía',
      subtitulo: 'Mueve existencias entre posiciones, pasillos o zonas. El sistema valida origen y destino.',
      cuerpo: `<form id="formTraslado"><div class="form-grid">
        <label class="field span-2"><span>Producto *</span><select class="select" id="trasProducto">${catalogo.productos.map((producto) => `<option value="${producto.id}">${esc(producto.nombre)} · ${esc(producto.sku)}</option>`).join('')}</select></label>
        <label class="field"><span>Origen *</span><select class="select" id="trasOrigen">${opcionesUbicacion}</select></label>
        <label class="field"><span>Destino *</span><select class="select" id="trasDestino">${opcionesUbicacion}</select></label>
        <label class="field"><span>Cantidad *</span><input class="input" id="trasCantidad" type="number" min="1" step="1" value="1" required></label>
        <label class="field"><span>Comentario</span><input class="input" id="trasComentario" maxlength="500" placeholder="Motivo del traslado"></label>
      </div><p class="form-error" id="errorTraslado"></p></form>`,
      acciones: '<button class="btn btn-ghost" type="button" id="cancelarTraslado">Cancelar</button><button class="btn btn-primary" type="button" id="guardarTraslado">Registrar traslado</button>',
    });
    if ($('#trasDestino').options.length > 1) $('#trasDestino').selectedIndex = 1;
    $('#cancelarTraslado').onclick = cerrarModal;
    $('#guardarTraslado').onclick = async () => {
      const boton = $('#guardarTraslado');
      const restaurar = bloquear(boton, 'Trasladando…');
      try {
        await api('/inventario/traslados', { method: 'POST', body: JSON.stringify({
          producto_id: Number($('#trasProducto').value),
          cantidad: Number($('#trasCantidad').value),
          ubicacion_origen_id: Number($('#trasOrigen').value),
          ubicacion_destino_id: Number($('#trasDestino').value),
          comentario: $('#trasComentario').value.trim() || null,
        }) });
        toast('Traslado registrado y stock actualizado.', 'success');
        cerrarModal(); renderSeccion();
      } catch (error) { $('#errorTraslado').textContent = error.message; toast(error.message, 'error'); restaurar(); }
    };
  } catch (error) { toast(error.message, 'error'); }
}

async function abrirMovimientoInventario() {
  try {
    const catalogo = await api('/inventario/catalogo');
    abrirModal({
      titulo: 'Registrar movimiento de almacén',
      subtitulo: 'El stock se actualiza automáticamente mediante el trigger de PostgreSQL.',
      cuerpo: `<form id="formMovimiento"><div class="form-grid">
        <label class="field span-2"><span>Producto *</span><select class="select" id="movProducto">${catalogo.productos.map((p) => `<option value="${p.id}">${esc(p.nombre)} · ${esc(p.sku)}</option>`).join('')}</select></label>
        <label class="field"><span>Ubicación *</span><select class="select" id="movUbicacion">${catalogo.ubicaciones.map((u) => `<option value="${u.id}">${esc(u.codigo)} · pasillo ${esc(u.pasillo)}</option>`).join('')}</select></label>
        <label class="field"><span>Tipo *</span><select class="select" id="movTipo"><option value="ENTRADA">Entrada</option><option value="SALIDA">Salida</option></select></label>
        <label class="field"><span>Cantidad *</span><input class="input" id="movCantidad" type="number" min="1" step="1" value="1" required></label>
      </div><p class="form-error" id="errorMovimiento"></p></form>`,
      acciones: '<button class="btn btn-ghost" type="button" id="cancelarMovimiento">Cancelar</button><button class="btn btn-primary" type="button" id="guardarMovimiento">Registrar movimiento</button>',
    });
    $('#cancelarMovimiento').onclick = cerrarModal;
    $('#guardarMovimiento').onclick = async () => {
      const boton = $('#guardarMovimiento');
      const restaurar = bloquear(boton, 'Registrando…');
      try {
        await api('/inventario/movimientos', { method: 'POST', body: JSON.stringify({
          producto_id: Number($('#movProducto').value),
          ubicacion_id: Number($('#movUbicacion').value),
          tipo: $('#movTipo').value,
          cantidad: Number($('#movCantidad').value),
        }) });
        toast('Movimiento registrado y stock actualizado.', 'success');
        cerrarModal(); renderSeccion();
      } catch (error) { $('#errorMovimiento').textContent = error.message; toast(error.message, 'error'); restaurar(); }
    };
  } catch (error) { toast(error.message, 'error'); }
}

/* --------------------------------------------------------------------------
   Auditoría
   -------------------------------------------------------------------------- */
PAGINAS.auditoria = async function (version) {
  if (!['admin', 'auditor'].includes(estado.usuario?.rol)) {
    $('#appContent').innerHTML = `<div class="panel panel-pad">${estadoVacio('alerta', 'Acceso restringido', 'La bitácora y los conteos están disponibles para administradores y auditores.')}</div>`;
    return;
  }
  const [bitacora, conteos, rotacion] = await Promise.all([
    api('/auditoria/bitacora?limite=250'),
    api('/auditoria/conteos?limite=80'),
    api('/auditoria/rotacion?limite=80'),
  ]);
  if (!vigente(version)) return;
  estado.auditoriaDatos = { bitacora, conteos, rotacion };
  renderPaginaAuditoria();
};

function renderPaginaAuditoria() {
  const datos = estado.auditoriaDatos || { bitacora: [], conteos: [], rotacion: [] };
  const tab = estado.auditoriaTab || 'bitacora';
  const tabs = [
    ['bitacora', 'Bitácora', datos.bitacora.length],
    ['conteos', 'Conteos cíclicos', datos.conteos.length],
    ['rotacion', 'Rotación', datos.rotacion.length],
  ];
  const contenido = tab === 'bitacora' ? tablaBitacora(datos.bitacora)
    : tab === 'conteos' ? tablaConteos(datos.conteos)
    : tablaRotacion(datos.rotacion);

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div><p class="eyebrow">Control interno</p><h1>Auditoría</h1><p class="muted">Registro de actividades, conteos cíclicos y métricas de rotación de inventario.</p></div>
      <div class="page-head-actions"><button class="btn btn-primary" type="button" id="nuevoConteo">${ico('mas')} Registrar conteo</button></div>
    </div>
    <section class="panel panel-pad">
      <div class="mini-tabs">${tabs.map(([valor, etiqueta, total]) => `<button class="mini-tab ${tab === valor ? 'active' : ''}" type="button" data-tab="${valor}">${etiqueta} · ${total}</button>`).join('')}</div>
      ${tab === 'bitacora' ? `<div class="audit-filters"><input class="input" id="filtroBitacora" placeholder="Filtrar por usuario, acción o entidad…"></div>` : ''}
      ${contenido}
    </section>`;

  $$('[data-tab]').forEach((boton) => boton.addEventListener('click', () => {
    estado.auditoriaTab = boton.dataset.tab;
    renderPaginaAuditoria();
  }));
  $('#filtroBitacora')?.addEventListener('input', (evento) => {
    const termino = evento.target.value.toLowerCase();
    $$('[data-bitacora-texto]').forEach((fila) => {
      fila.style.display = fila.dataset.bitacoraTexto.includes(termino) ? '' : 'none';
    });
  });
  $('#nuevoConteo')?.addEventListener('click', abrirNuevoConteo);
}

function tablaBitacora(filas) {
  if (!filas.length) return estadoVacio('auditoria', 'Sin registros', 'Las acciones del sistema aparecerán en la bitácora.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Fecha</th><th>Usuario</th><th>Rol</th><th>Acción</th><th>Entidad</th><th>Detalle</th></tr></thead>
    <tbody>${filas.map((fila) => {
      const detalle = Object.entries(fila.detalle || {}).map(([clave, valor]) => `${clave}: ${valor}`).join(' · ');
      return `<tr data-bitacora-texto="${esc(`${fila.usuario} ${fila.accion} ${fila.entidad || ''} ${detalle}`.toLowerCase())}">
        <td class="nowrap">${esc(fechaHora(fila.fecha))}</td>
        <td class="primary-cell">${esc(fila.usuario)}</td>
        <td>${badgeRol(fila.rol)}</td>
        <td><span class="badge simple">${esc(fila.accion)}</span></td>
        <td>${esc(fila.entidad || '—')}${fila.entidad_id ? `<span class="sub">#${esc(fila.entidad_id)}</span>` : ''}</td>
        <td class="tiny muted" style="max-width:360px">${esc(detalle || '—')}</td>
      </tr>`;
    }).join('')}</tbody></table></div>`;
}

function tablaConteos(filas) {
  if (!filas.length) return estadoVacio('auditoria', 'Sin conteos', 'Registra el primer conteo cíclico para comparar físico contra sistema.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Fecha</th><th>Ubicación</th><th>Producto</th><th>Sistema</th><th>Físico</th><th>Diferencia</th><th>Auditor</th></tr></thead>
    <tbody>${filas.map((fila) => `<tr>
      <td class="nowrap">${esc(fechaHora(fila.fecha))}</td><td class="mono">${esc(fila.ubicacion)}</td><td class="primary-cell">${esc(fila.producto)}</td>
      <td>${numero(fila.cantidad_sistema)}</td><td>${numero(fila.cantidad_fisica)}</td>
      <td><span class="badge ${fila.diferencia === 0 ? 'entregado' : 'fallido'}">${fila.diferencia > 0 ? '+' : ''}${numero(fila.diferencia)}</span></td>
      <td>${esc(fila.auditor)}</td></tr>`).join('')}</tbody></table></div>`;
}

function tablaRotacion(filas) {
  if (!filas.length) return estadoVacio('reportes', 'Sin métricas', 'Las métricas aparecerán cuando existan movimientos.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>SKU</th><th>Producto</th><th>Salidas</th><th>Entradas</th><th>Rotación</th></tr></thead>
    <tbody>${filas.map((fila) => {
      const total = Number(fila.total_salidas) + Number(fila.total_entradas);
      const pct = total ? Math.round((Number(fila.total_salidas) / total) * 100) : 0;
      return `<tr><td class="mono">${esc(fila.sku)}</td><td class="primary-cell">${esc(fila.nombre)}</td><td>${numero(fila.total_salidas)}</td><td>${numero(fila.total_entradas)}</td><td><div class="stock-bar"><span>${pct}%</span><div class="stock-track"><div class="stock-fill" style="width:${pct}%"></div></div></div></td></tr>`;
    }).join('')}</tbody></table></div>`;
}

async function abrirNuevoConteo() {
  try {
    const catalogo = await api('/inventario/catalogo');
    abrirModal({
      titulo: 'Registrar conteo cíclico',
      subtitulo: 'La cantidad de sistema se obtiene del stock actual; captura únicamente lo contado físicamente.',
      cuerpo: `<form id="formConteo"><div class="form-grid">
        <label class="field span-2"><span>Producto *</span><select class="select" id="conteoProducto">${catalogo.productos.map((p) => `<option value="${p.id}">${esc(p.nombre)} · ${esc(p.sku)}</option>`).join('')}</select></label>
        <label class="field"><span>Ubicación *</span><select class="select" id="conteoUbicacion">${catalogo.ubicaciones.map((u) => `<option value="${u.id}">${esc(u.codigo)} · pasillo ${esc(u.pasillo)}</option>`).join('')}</select></label>
        <label class="field"><span>Cantidad física *</span><input class="input" id="conteoCantidad" type="number" min="0" step="1" value="0" required></label>
      </div><p class="form-error" id="errorConteo"></p></form>`,
      acciones: '<button class="btn btn-ghost" type="button" id="cancelarConteo">Cancelar</button><button class="btn btn-primary" type="button" id="guardarConteo">Registrar conteo</button>',
    });
    $('#cancelarConteo').onclick = cerrarModal;
    $('#guardarConteo').onclick = async () => {
      const boton = $('#guardarConteo');
      const restaurar = bloquear(boton, 'Registrando…');
      try {
        await api('/auditoria/conteos', { method: 'POST', body: JSON.stringify({
          producto_id: Number($('#conteoProducto').value),
          ubicacion_id: Number($('#conteoUbicacion').value),
          cantidad_fisica: Number($('#conteoCantidad').value),
        }) });
        toast('Conteo cíclico registrado.', 'success');
        cerrarModal(); renderSeccion();
      } catch (error) { $('#errorConteo').textContent = error.message; toast(error.message, 'error'); restaurar(); }
    };
  } catch (error) { toast(error.message, 'error'); }
}

/* --------------------------------------------------------------------------
   Usuarios
   -------------------------------------------------------------------------- */
PAGINAS.usuarios = async function (version) {
  if (!esAdmin()) {
    $('#appContent').innerHTML = `<div class="panel panel-pad">${estadoVacio('alerta', 'Acceso restringido', 'Solo el rol Administrador puede gestionar usuarios del sistema.')}</div>`;
    return;
  }
  const usuarios = await api('/usuarios');
  if (!vigente(version)) return;
  const activos = usuarios.filter((usuario) => usuario.activo).length;
  const filas = usuarios.map((usuario) => `
    <tr>
      <td class="primary-cell">${esc(usuario.nombre)}<span class="sub">${esc(usuario.usuario)}</span></td>
      <td>${esc(usuario.correo || '—')}</td>
      <td>${badgeRol(usuario.rol)}</td>
      <td>${esc(usuario.puesto || '—')}</td>
      <td>${usuario.activo ? '<span class="badge completada">Activo</span>' : '<span class="badge cancelada">Inactivo</span>'}</td>
      <td class="text-right nowrap"><button class="btn btn-small btn-ghost" type="button" data-editar-usuario="${usuario.id}">Editar</button><button class="btn btn-small ${usuario.activo ? 'btn-danger' : 'btn-success'}" type="button" data-toggle-user="${usuario.id}" data-activo="${usuario.activo}" data-nombre="${esc(usuario.nombre)}">${usuario.activo ? 'Desactivar' : 'Activar'}</button></td>
    </tr>`).join('');

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div><p class="eyebrow">Seguridad</p><h1>Usuarios y roles</h1><p class="muted">Administra el acceso al sistema. Los tres roles base son Administrador, Operador y Auditor.</p></div>
      <div class="page-head-actions"><button class="btn btn-primary" type="button" id="nuevoUsuario">${ico('mas')} Nuevo usuario</button></div>
    </div>
    <div class="grid grid-kpi">
      ${kpiCard({ clase: 'blue', icono: 'usuarios', etiqueta: 'Usuarios totales', valor: numero(usuarios.length), detalle: `${numero(activos)} activos` })}
      ${kpiCard({ clase: 'green', icono: 'llave', etiqueta: 'Administradores', valor: numero(usuarios.filter((u) => u.rol === 'admin').length), detalle: 'control total' })}
      ${kpiCard({ clase: 'orange', icono: 'rutas', etiqueta: 'Operadores', valor: numero(usuarios.filter((u) => u.rol === 'operador').length), detalle: 'operación diaria' })}
      ${kpiCard({ clase: 'purple', icono: 'auditoria', etiqueta: 'Auditores', valor: numero(usuarios.filter((u) => u.rol === 'auditor').length), detalle: 'solo lectura y conteos' })}
    </div>
    <section class="panel panel-pad section-gap">${encabezadoPanel('Cuentas del sistema', 'El backend valida el rol en cada petición y PostgreSQL aplica los GRANT.')}
      <div class="table-wrap"><table class="data-table"><thead><tr><th>Usuario</th><th>Correo</th><th>Rol</th><th>Puesto</th><th>Estado</th><th></th></tr></thead><tbody>${filas}</tbody></table></div>
    </section>`;

  $('#nuevoUsuario')?.addEventListener('click', abrirNuevoUsuario);
  $$('[data-toggle-user]').forEach((boton) => boton.addEventListener('click', () => cambiarEstadoUsuario(
    Number(boton.dataset.toggleUser), boton.dataset.activo === 'true', boton.dataset.nombre,
  )));
  $$('[data-editar-usuario]').forEach((boton) => boton.addEventListener('click', () => {
    const usuario = usuarios.find((item) => item.id === Number(boton.dataset.editarUsuario));
    if (usuario) abrirEditarUsuario(usuario);
  }));
};

function abrirEditarUsuario(usuario) {
  abrirModal({
    titulo: `Editar ${usuario.usuario}`,
    subtitulo: 'Cambia nombre, correo, rol o contraseña. La baja lógica se controla con el botón Activar/Desactivar.',
    cuerpo: `<form id="formEditarUsuario"><div class="form-grid">
      <label class="field span-2"><span>Nombre completo *</span><input class="input" id="eusNombre" maxlength="120" value="${esc(usuario.nombre)}" required></label>
      <label class="field span-2"><span>Correo</span><input class="input" id="eusCorreo" type="email" maxlength="160" value="${esc(usuario.correo || '')}"></label>
      <label class="field"><span>Rol *</span><select class="select" id="eusRol"><option value="operador" ${usuario.rol === 'operador' ? 'selected' : ''}>Operador</option><option value="auditor" ${usuario.rol === 'auditor' ? 'selected' : ''}>Auditor</option><option value="admin" ${usuario.rol === 'admin' ? 'selected' : ''}>Administrador</option></select></label>
      <label class="field"><span>Puesto *</span><select class="select" id="eusPuesto">${opciones(['Auxiliar de almacén', 'Montacarguista', 'Surtidor', 'Empacador', 'Chofer', 'Supervisor', 'Administración', 'Dirección', 'Auditoría'], usuario.puesto || 'Administración')}</select></label>
      <label class="field"><span>Nueva contraseña</span><input class="input" id="eusContrasena" type="password" minlength="8" maxlength="200" placeholder="Opcional"></label>
    </div><p class="form-error" id="errorEditarUsuario"></p></form>`,
    acciones: '<button class="btn btn-ghost" type="button" id="cancelarEditarUsuario">Cancelar</button><button class="btn btn-primary" type="button" id="guardarEditarUsuario">Guardar cambios</button>',
  });
  $('#cancelarEditarUsuario').onclick = cerrarModal;
  $('#guardarEditarUsuario').onclick = async () => {
    const boton = $('#guardarEditarUsuario');
    const restaurar = bloquear(boton, 'Guardando…');
    try {
      await api(`/usuarios/${usuario.id}`, { method: 'PATCH', body: JSON.stringify({
        nombre: $('#eusNombre').value.trim(), correo: $('#eusCorreo').value.trim() || null,
        rol: $('#eusRol').value, puesto: $('#eusPuesto').value,
        contrasena: $('#eusContrasena').value || null,
      }) });
      toast('Usuario actualizado.', 'success'); cerrarModal(); renderSeccion();
    } catch (error) { $('#errorEditarUsuario').textContent = error.message; toast(error.message, 'error'); restaurar(); }
  };
}

async function cambiarEstadoUsuario(usuarioId, activo, nombre) {
  if (activo && !window.confirm(`¿Desactivar la cuenta de ${nombre}?`)) return;
  try {
    await api(`/usuarios/${usuarioId}/estado`, { method: 'PATCH', body: JSON.stringify({ activo: !activo }) });
    toast(activo ? 'Usuario desactivado.' : 'Usuario activado.', 'success');
    renderSeccion();
  } catch (error) { toast(error.message, 'error'); }
}

function abrirNuevoUsuario() {
  abrirModal({
    titulo: 'Crear usuario',
    subtitulo: 'La contraseña se almacena con PBKDF2-SHA256, nunca en texto plano.',
    cuerpo: `<form id="formUsuario"><div class="form-grid">
      <label class="field span-2"><span>Nombre completo *</span><input class="input" id="usrNombre" maxlength="120" placeholder="Ana Torres" required></label>
      <label class="field"><span>Usuario *</span><input class="input" id="usrUsuario" maxlength="40" placeholder="ana.torres" required></label>
      <label class="field"><span>Correo</span><input class="input" id="usrCorreo" type="email" maxlength="160" placeholder="ana@logistixpress.mx"></label>
      <label class="field"><span>Contraseña *</span><input class="input" id="usrContrasena" type="password" minlength="8" maxlength="200" placeholder="Mínimo 8 caracteres" required></label>
      <label class="field"><span>Rol *</span><select class="select" id="usrRol"><option value="operador">Operador</option><option value="auditor">Auditor</option><option value="admin">Administrador</option></select></label>
      <label class="field"><span>Puesto *</span><select class="select" id="usrPuesto"><option value="Auxiliar de almacén">Auxiliar de almacén</option><option value="Montacarguista">Montacarguista</option><option value="Surtidor">Surtidor</option><option value="Empacador">Empacador</option><option value="Chofer">Chofer</option><option value="Supervisor" selected>Supervisor</option><option value="Administración">Administración</option><option value="Dirección">Dirección</option><option value="Auditoría">Auditoría</option></select></label>
    </div><p class="form-error" id="errorUsuario"></p></form>`,
    acciones: '<button class="btn btn-ghost" type="button" id="cancelarUsuario">Cancelar</button><button class="btn btn-primary" type="button" id="guardarUsuario">Crear usuario</button>',
  });
  $('#cancelarUsuario').onclick = cerrarModal;
  $('#guardarUsuario').onclick = async () => {
    const boton = $('#guardarUsuario');
    const restaurar = bloquear(boton, 'Creando…');
    try {
      await api('/usuarios', { method: 'POST', body: JSON.stringify({
        nombre: $('#usrNombre').value.trim(), usuario: $('#usrUsuario').value.trim(),
        correo: $('#usrCorreo').value.trim() || null, contrasena: $('#usrContrasena').value, rol: $('#usrRol').value,
        puesto: $('#usrPuesto').value,
      }) });
      toast('Usuario creado.', 'success'); cerrarModal(); renderSeccion();
    } catch (error) { $('#errorUsuario').textContent = error.message; toast(error.message, 'error'); restaurar(); }
  };
}

/* --------------------------------------------------------------------------
   Reportes
   -------------------------------------------------------------------------- */
const CATALOGO_REPORTES = [
  { tipo: 'rutas', titulo: 'Rutas y desempeño', descripcion: 'Planificación, distancia, ahorro y estado de las rutas.', icono: 'rutas', roles: ['admin', 'operador'], fechas: true },
  { tipo: 'entregas', titulo: 'Entregas y evidencias', descripcion: 'Resultados, motivos de falla y reprogramaciones.', icono: 'check', roles: ['admin', 'operador'], fechas: true },
  { tipo: 'inventario', titulo: 'Inventario por producto', descripcion: 'Existencias, mínimos, ubicaciones y próximos vencimientos.', icono: 'inventario', roles: ['admin', 'operador', 'auditor'], fechas: false },
  { tipo: 'movimientos', titulo: 'Movimientos de almacén', descripcion: 'Historial de entradas y salidas por producto y usuario.', icono: 'reportes', roles: ['admin', 'operador', 'auditor'], fechas: true },
  { tipo: 'auditoria', titulo: 'Bitácora de actividades', descripcion: 'Acciones por usuario, rol, entidad y detalle.', icono: 'auditoria', roles: ['admin', 'auditor'], fechas: true },
  { tipo: 'rotacion', titulo: 'Métricas de rotación', descripcion: 'Entradas y salidas acumuladas por producto.', icono: 'reportes', roles: ['admin', 'auditor'], fechas: false },
  { tipo: 'usuarios', titulo: 'Usuarios del sistema', descripcion: 'Cuentas, rol y estado de acceso.', icono: 'usuarios', roles: ['admin'], fechas: false },
];

PAGINAS.reportes = async function (version) {
  const disponibles = CATALOGO_REPORTES.filter((reporte) => reporte.roles.includes(estado.usuario?.rol));
  if (!vigente(version)) return;
  const tarjetas = disponibles.length
    ? `<div class="report-grid">${disponibles.map((reporte) => `
        <article class="panel report-card">
          <span class="report-icon">${ico(reporte.icono)}</span>
          <h3>${esc(reporte.titulo)}</h3>
          <p>${esc(reporte.descripcion)}</p>
          <div class="report-actions">
            <button class="btn btn-small btn-primary" type="button" data-reporte="${reporte.tipo}" data-formato="pdf">${ico('descargar')} PDF</button>
            <button class="btn btn-small btn-ghost" type="button" data-reporte="${reporte.tipo}" data-formato="xlsx">${ico('descargar')} Excel</button>
          </div>
        </article>`).join('')}</div>`
    : estadoVacio('reportes', 'Sin reportes disponibles', 'Tu rol no tiene reportes configurados.');

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div><p class="eyebrow">Documentos</p><h1>Reportes</h1><p class="muted">Genera PDF o Excel desde el backend. Los permisos se validan con tu rol de sesión.</p></div>
    </div>
    <section class="panel panel-pad">
      ${encabezadoPanel('Periodo de exportación', 'Aplica a rutas, entregas y bitácora. Inventario y rotación usan el estado actual.')}
      <div class="date-range">
        <label class="field"><span>Desde</span><input class="input" type="date" id="repDesde" value="${hoyISO().slice(0, 8)}01"></label>
        <label class="field"><span>Hasta</span><input class="input" type="date" id="repHasta" value="${hoyISO()}"></label>
      </div>
    </section>
    <div class="section-gap">${tarjetas}</div>
    <section class="panel panel-pad section-gap">
      ${encabezadoPanel('Historial de esta sesión', 'Descargas realizadas desde este navegador.')}
      <div class="export-history" id="historialReportes"></div>
    </section>`;

  renderHistorialReportes();
  $$('[data-reporte]').forEach((boton) => boton.addEventListener('click', () => descargarReporte(
    boton.dataset.reporte, boton.dataset.formato, boton,
  )));
};

async function descargarReporte(tipo, formato, boton) {
  const reporte = CATALOGO_REPORTES.find((item) => item.tipo === tipo);
  const parametros = new URLSearchParams({ tipo, formato });
  if (reporte?.fechas) {
    const desde = $('#repDesde').value;
    const hasta = $('#repHasta').value;
    if (!desde || !hasta || desde > hasta) { toast('Revisa el rango de fechas del reporte.', 'error'); return; }
    parametros.set('desde', desde);
    parametros.set('hasta', hasta);
  }
  const restaurar = bloquear(boton, 'Generando…');
  try {
    const blob = await apiBlob(`/reportes/exportar?${parametros.toString()}`);
    const nombre = `reporte_${tipo}_${hoyISO()}.${formato}`;
    await descargarBlob(blob, nombre);
    estado.reportesHistorial.unshift({ nombre, tipo, formato, fecha: new Date().toISOString(), ok: true });
    estado.reportesHistorial = estado.reportesHistorial.slice(0, 20);
    sessionStorage.setItem('royal_reportes', JSON.stringify(estado.reportesHistorial));
    renderHistorialReportes();
    toast(`Reporte ${formato.toUpperCase()} descargado.`, 'success');
  } catch (error) {
    toast(error.message, 'error');
  } finally { restaurar(); }
}

function renderHistorialReportes() {
  const contenedor = $('#historialReportes');
  if (!contenedor) return;
  if (!estado.reportesHistorial.length) {
    contenedor.innerHTML = '<p class="muted tiny">Sin reportes generados en esta sesión.</p>';
    return;
  }
  contenedor.innerHTML = estado.reportesHistorial.map((item) => `
    <div class="export-item">${ico('descargar')}<div><strong>${esc(item.nombre)}</strong><small>${esc(fechaHora(item.fecha))}</small></div></div>`).join('');
}

/* --------------------------------------------------------------------------
   Perfil
   -------------------------------------------------------------------------- */
PAGINAS.perfil = async function (version) {
  let salud = { base_datos: false, version: '—' };
  try { salud = await api('/salud'); } catch { /* la vista sigue disponible */ }
  if (!vigente(version)) return;
  const usuario = estado.usuario || {};
  const permisos = [
    ['Generar y replanificar rutas', 'admin', 'operador', null],
    ['Despachar y validar escaneo', 'admin', 'operador', null],
    ['Registrar entregas y evidencias', 'admin', 'operador', null],
    ['Movimientos de inventario', 'admin', 'operador', null],
    ['Bitácora y conteos', 'admin', null, 'auditor'],
    ['Gestión de usuarios', 'admin', null, null],
  ];
  const marca = (permitido) => permitido ? `<span class="badge completada">Sí</span>` : `<span class="badge simple">No</span>`;

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div><p class="eyebrow">Cuenta</p><h1>Mi perfil</h1><p class="muted">Datos de la sesión y alcance de tu rol dentro del sistema.</p></div>
      <button class="btn btn-danger" type="button" id="perfilSalir">${ico('salir')} Cerrar sesión</button>
    </div>
    <div class="grid grid-main">
      <section class="panel panel-pad">
        <div style="display:flex;gap:14px;align-items:center;margin-bottom:18px">
          <span class="avatar" style="width:54px;height:54px;flex-basis:54px;font-size:15px">${esc(iniciales(usuario.nombre))}</span>
          <div><h2>${esc(usuario.nombre || 'Usuario')}</h2><p class="muted">${esc(usuario.correo || 'Sin correo registrado')}</p></div>
        </div>
        <div class="info-grid">
          <div class="info-item"><span>Usuario</span><strong class="mono">${esc(usuario.usuario || '—')}</strong></div>
          <div class="info-item"><span>Rol</span><strong>${esc(ROL_LABEL[usuario.rol] || usuario.rol || '—')}</strong></div>
          <div class="info-item"><span>API local</span><strong class="mono">${esc(API_BASE)}</strong></div>
          <div class="info-item"><span>Versión backend</span><strong>${esc(salud.version || '—')}</strong></div>
          <div class="info-item"><span>PostgreSQL</span><strong>${salud.base_datos ? '<span class="badge completada">Conectado</span>' : '<span class="badge fallido">Sin conexión</span>'}</strong></div>
          <div class="info-item"><span>Token</span><strong>${estado.token ? '<span class="badge completada">Sesión activa</span>' : '<span class="badge simple">Sin sesión</span>'}</strong></div>
        </div>
      </section>
      <section class="panel panel-pad">
        ${encabezadoPanel('Alcance del rol', 'El backend y PostgreSQL validan estos permisos en cada operación.')}
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Capacidad</th><th>Admin</th><th>Operador</th><th>Auditor</th></tr></thead><tbody>
          ${permisos.map(([nombre, admin, operador, auditor]) => `<tr><td class="primary-cell">${esc(nombre)}</td><td>${marca(Boolean(admin))}</td><td>${marca(Boolean(operador))}</td><td>${marca(Boolean(auditor))}</td></tr>`).join('')}
        </tbody></table></div>
      </section>
    </div>
    <section class="panel panel-pad section-gap">
      ${encabezadoPanel('Sobre esta aplicación', 'PoC académico de WMS y reparto para LogistiXpress.')}
      <p class="inline-note">El dashboard corre en loopback y consume la API FastAPI. Las rutas se consolidan por zona y tipo de cliente, se optimizan con vecino más cercano + 2-opt y se renderizan como PNG con matplotlib. Las entregas guardan firma y fotografía en el servidor local.</p>
    </section>`;

  $('#perfilSalir').addEventListener('click', salir);
};
