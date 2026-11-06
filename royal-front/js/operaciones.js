'use strict';

/* ==========================================================================
   Operaciones extendidas: maestros, recepción y picking/packing
   ========================================================================== */

const TIPOS_CLIENTE = ['MINORISTA', 'MAYORISTA', 'FARMACIA', 'RESTAURANTE', 'CORPORATIVO', 'HOSPITAL'];
const ZONAS_CLIENTE = ['NORTE', 'SUR', 'ORIENTE', 'PONIENTE'];
const TIPOS_ZONA = ['GENERAL', 'DEVOLUCIONES', 'DANADOS', 'BLOQUEADO', 'RESERVADO'];
const CONDICIONES_LOTE = ['BUENO', 'DANADO', 'INCOMPLETO'];
const MOTIVOS_INCIDENCIA = ['Caja rota', 'Producto dañado', 'Faltante', 'Producto incorrecto', 'Otro'];


function opcionesProductos(productos, actual) {
  return productos.map((producto) => (
    `<option value="${producto.id}" ${Number(producto.id) === Number(actual) ? 'selected' : ''}>${esc(producto.nombre)} · ${esc(producto.sku)}</option>`
  )).join('');
}

function opcionesClientes(clientes, actual) {
  return clientes.map((cliente) => (
    `<option value="${cliente.id}" ${Number(cliente.id) === Number(actual) ? 'selected' : ''}>${esc(cliente.nombre)} · ${esc(cliente.codigo)}</option>`
  )).join('');
}

function opcionesUbicaciones(ubicaciones, actual, soloGeneral = false) {
  return ubicaciones
    .filter((ubicacion) => !soloGeneral || ubicacion.tipo_zona === 'GENERAL')
    .map((ubicacion) => (
      `<option value="${ubicacion.id}" ${Number(ubicacion.id) === Number(actual) ? 'selected' : ''}>${esc(ubicacion.codigo)} · ${esc(ubicacion.tipo_zona)}</option>`
    )).join('');
}

function zonaChip(zona) {
  const especial = zona && zona !== 'GENERAL';
  return `<span class="zone-chip ${especial ? 'especial' : ''}">${esc(zona || 'GENERAL')}</span>`;
}

function agregarFilaLinea(contenedor, productos, productoId = null, cantidad = 1) {
  const fila = document.createElement('div');
  fila.className = 'line-editor-row';
  fila.innerHTML = `
    <label class="field"><span>Producto</span><select class="select linea-producto">${opcionesProductos(productos, productoId)}</select></label>
    <label class="field"><span>Cantidad</span><input class="input linea-cantidad" type="number" min="1" step="1" value="${numero(cantidad)}"></label>
    <button class="icon-button" type="button" title="Quitar línea">${ico('x')}</button>`;
  fila.querySelector('button').onclick = () => {
    if (contenedor.children.length > 1) fila.remove();
  };
  contenedor.appendChild(fila);
}

function leerLineasEditor(contenedor) {
  return [...contenedor.querySelectorAll('.line-editor-row')]
    .map((fila) => ({
      producto_id: Number(fila.querySelector('.linea-producto').value),
      cantidad: Number(fila.querySelector('.linea-cantidad').value),
    }))
    .filter((linea) => linea.producto_id > 0 && linea.cantidad > 0);
}

async function enviarFormulario(boton, errorBox, peticion, mensaje) {
  const restaurar = bloquear(boton, 'Guardando…');
  try {
    await peticion();
    toast(mensaje, 'success');
    cerrarModal();
    renderSeccion();
  } catch (error) {
    errorBox.textContent = error.message;
    toast(error.message, 'error');
    restaurar();
  }
}

/* --------------------------------------------------------------------------
   Maestros
   -------------------------------------------------------------------------- */
PAGINAS.maestros = async function (version) {
  const [clientes, productos, ubicaciones, lotes, proveedores, pedidos] = await Promise.all([
    api('/maestros/clientes'),
    api('/maestros/productos'),
    api('/maestros/ubicaciones'),
    api('/maestros/lotes'),
    api('/maestros/proveedores'),
    api('/maestros/pedidos?limite=100'),
  ]);
  if (!vigente(version)) return;
  estado.maestrosDatos = { clientes, productos, ubicaciones, lotes, proveedores, pedidos };
  if (!estado.maestrosTab) estado.maestrosTab = 'clientes';
  renderPaginaMaestros();
};

function renderPaginaMaestros() {
  const datos = estado.maestrosDatos || {};
  const tabs = [
    ['clientes', 'Clientes', (datos.clientes || []).length],
    ['productos', 'Productos', (datos.productos || []).length],
    ['ubicaciones', 'Ubicaciones', (datos.ubicaciones || []).length],
    ['lotes', 'Lotes', (datos.lotes || []).length],
    ['proveedores', 'Proveedores', (datos.proveedores || []).length],
    ['pedidos', 'Pedidos', (datos.pedidos || []).length],
  ];
  const tab = estado.maestrosTab || 'clientes';
  const botones = {
    clientes: puedeOperar() ? `<button class="btn btn-primary" type="button" id="nuevoRegistro">${ico('mas')} Nuevo cliente</button>` : '',
    productos: esAdmin() ? `<button class="btn btn-primary" type="button" id="nuevoRegistro">${ico('mas')} Nuevo producto</button>` : '',
    ubicaciones: esAdmin() ? `<button class="btn btn-primary" type="button" id="nuevoRegistro">${ico('mas')} Nueva ubicación</button>` : '',
    lotes: puedeOperar() ? `<button class="btn btn-primary" type="button" id="nuevoRegistro">${ico('mas')} Nuevo lote</button>` : '',
    proveedores: puedeOperar() ? `<button class="btn btn-primary" type="button" id="nuevoRegistro">${ico('mas')} Nuevo proveedor</button>` : '',
    pedidos: puedeOperar() ? `<button class="btn btn-primary" type="button" id="nuevoRegistro">${ico('mas')} Nuevo pedido</button>` : '',
  };
  const contenido = {
    clientes: tablaClientes(datos.clientes || []),
    productos: tablaProductos(datos.productos || []),
    ubicaciones: tablaUbicaciones(datos.ubicaciones || []),
    lotes: tablaLotes(datos.lotes || []),
    proveedores: tablaProveedores(datos.proveedores || []),
    pedidos: tablaPedidos(datos.pedidos || []),
  };

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div>
        <p class="eyebrow">Datos maestros</p>
        <h1>Maestros y pedidos</h1>
        <p class="muted">CRUD de clientes, productos, ubicaciones, lotes, proveedores y pedidos. Los cambios quedan en bitácora.</p>
      </div>
      <div class="page-head-actions">${botones[tab] || ''}</div>
    </div>
    <section class="panel panel-pad">
      <div class="mini-tabs">${tabs.map(([valor, etiqueta, total]) => `<button class="mini-tab ${tab === valor ? 'active' : ''}" type="button" data-maestro-tab="${valor}">${etiqueta} · ${total}</button>`).join('')}</div>
      ${contenido[tab] || ''}
    </section>`;

  $$('[data-maestro-tab]').forEach((boton) => boton.addEventListener('click', () => {
    estado.maestrosTab = boton.dataset.maestroTab;
    renderPaginaMaestros();
  }));
  $('#nuevoRegistro')?.addEventListener('click', () => {
    if (tab === 'clientes') abrirFormularioCliente();
    else if (tab === 'productos') abrirFormularioProducto();
    else if (tab === 'ubicaciones') abrirFormularioUbicacion();
    else if (tab === 'lotes') abrirFormularioLote();
    else if (tab === 'proveedores') abrirFormularioProveedor();
    else if (tab === 'pedidos') abrirFormularioPedido();
  });
  $$('[data-editar-cliente]').forEach((boton) => boton.addEventListener('click', () => {
    const cliente = datos.clientes.find((item) => item.id === Number(boton.dataset.editarCliente));
    if (cliente) abrirFormularioCliente(cliente);
  }));
  $$('[data-editar-producto]').forEach((boton) => boton.addEventListener('click', () => {
    const producto = datos.productos.find((item) => item.id === Number(boton.dataset.editarProducto));
    if (producto) abrirFormularioProducto(producto);
  }));
  $$('[data-editar-ubicacion]').forEach((boton) => boton.addEventListener('click', () => {
    const ubicacion = datos.ubicaciones.find((item) => item.id === Number(boton.dataset.editarUbicacion));
    if (ubicacion) abrirFormularioUbicacion(ubicacion);
  }));
  $$('[data-editar-lote]').forEach((boton) => boton.addEventListener('click', () => {
    const lote = datos.lotes.find((item) => item.id === Number(boton.dataset.editarLote));
    if (lote) abrirFormularioLote(lote);
  }));
  $$('[data-editar-proveedor]').forEach((boton) => boton.addEventListener('click', () => {
    const proveedor = datos.proveedores.find((item) => item.id === Number(boton.dataset.editarProveedor));
    if (proveedor) abrirFormularioProveedor(proveedor);
  }));
  $$('[data-ver-pedido]').forEach((boton) => boton.addEventListener('click', () => {
    const pedido = datos.pedidos.find((item) => item.id === Number(boton.dataset.verPedido));
    if (pedido) verPedidoMaestro(pedido);
  }));
  $$('[data-editar-pedido]').forEach((boton) => boton.addEventListener('click', () => {
    abrirEditarPedido(Number(boton.dataset.editarPedido));
  }));
  $$('[data-cancelar-pedido]').forEach((boton) => boton.addEventListener('click', () => {
    const pedido = datos.pedidos.find((item) => item.id === Number(boton.dataset.cancelarPedido));
    if (pedido && window.confirm(`¿Cancelar el pedido ${pedido.folio}?`)) {
      api(`/maestros/pedidos/${pedido.id}/cancelar`, { method: 'POST' })
        .then(() => { toast('Pedido cancelado.', 'success'); renderSeccion(); })
        .catch((error) => toast(error.message, 'error'));
    }
  }));
}

function tablaClientes(clientes) {
  if (!clientes.length) return estadoVacio('usuarios', 'Sin clientes', 'Crea el primer cliente para asociar pedidos.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Código</th><th>Cliente</th><th>Tipo</th><th>Zona</th><th>Teléfono</th><th>Estado</th><th></th></tr></thead>
    <tbody>${clientes.map((cliente) => `<tr>
      <td class="mono">${esc(cliente.codigo)}</td>
      <td class="primary-cell">${esc(cliente.nombre)}<span class="sub">${esc(cliente.direccion)}</span></td>
      <td>${esc(cliente.tipo_cliente)}</td>
      <td>${badgeZona(cliente.zona)}</td>
      <td>${esc(cliente.telefono || '—')}</td>
      <td>${cliente.activo ? '<span class="badge completada">Activo</span>' : '<span class="badge cancelada">Inactivo</span>'}</td>
      <td class="text-right"><button class="btn btn-small btn-ghost" type="button" data-editar-cliente="${cliente.id}">Editar</button></td>
    </tr>`).join('')}</tbody></table></div>`;
}

function tablaProductos(productos) {
  if (!productos.length) return estadoVacio('inventario', 'Sin productos', 'Crea el primer producto del catálogo.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>SKU</th><th>Producto</th><th>Stock</th><th>Mínimo</th><th>Peso</th><th>Volumen</th><th>Estado</th><th></th></tr></thead>
    <tbody>${productos.map((producto) => `<tr>
      <td class="mono">${esc(producto.sku)}</td>
      <td class="primary-cell">${esc(producto.nombre)}</td>
      <td>${numero(producto.stock_total)}</td>
      <td>${numero(producto.stock_minimo)}</td>
      <td>${peso(producto.peso_kg)}</td>
      <td>${volumen(producto.volumen_m3)}</td>
      <td>${producto.activo ? '<span class="badge completada">Activo</span>' : '<span class="badge cancelada">Inactivo</span>'}</td>
      <td class="text-right">${esAdmin() ? `<button class="btn btn-small btn-ghost" type="button" data-editar-producto="${producto.id}">Editar</button>` : ''}</td>
    </tr>`).join('')}</tbody></table></div>`;
}

function tablaUbicaciones(ubicaciones) {
  if (!ubicaciones.length) return estadoVacio('edificio', 'Sin ubicaciones', 'Crea la primera posición de rack.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Código</th><th>Pasillo</th><th>Rack</th><th>Nivel</th><th>Zona</th><th>Stock</th><th>Estado</th><th></th></tr></thead>
    <tbody>${ubicaciones.map((ubicacion) => `<tr>
      <td class="mono primary-cell">${esc(ubicacion.codigo)}</td>
      <td>${esc(ubicacion.pasillo)}</td><td>${esc(ubicacion.rack)}</td><td>${numero(ubicacion.nivel)}</td>
      <td>${zonaChip(ubicacion.tipo_zona)}</td><td>${numero(ubicacion.stock_total)}</td>
      <td>${ubicacion.activo ? '<span class="badge completada">Activa</span>' : '<span class="badge cancelada">Inactiva</span>'}</td>
      <td class="text-right">${esAdmin() ? `<button class="btn btn-small btn-ghost" type="button" data-editar-ubicacion="${ubicacion.id}">Editar</button>` : ''}</td>
    </tr>`).join('')}</tbody></table></div>`;
}

function tablaLotes(lotes) {
  if (!lotes.length) return estadoVacio('inventario', 'Sin lotes', 'Registra lotes desde recepción o desde este maestro.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Lote</th><th>Producto</th><th>Ubicación</th><th>Caducidad</th><th>Cantidad</th><th>Condición</th><th></th></tr></thead>
    <tbody>${lotes.map((lote) => `<tr>
      <td class="mono primary-cell">${esc(lote.lote)}</td>
      <td>${esc(lote.producto)}<span class="sub">${esc(lote.sku)}</span></td>
      <td class="mono">${esc(lote.ubicacion)}</td>
      <td>${esc(fechaCorta(lote.caducidad))}</td>
      <td>${numero(lote.cantidad)}</td>
      <td><span class="badge ${lote.condicion === 'BUENO' ? 'entregado' : 'fallido'}">${esc(lote.condicion)}</span></td>
      <td class="text-right">${puedeOperar() ? `<button class="btn btn-small btn-ghost" type="button" data-editar-lote="${lote.id}">Editar</button>` : ''}</td>
    </tr>`).join('')}</tbody></table></div>`;
}

function tablaProveedores(proveedores) {
  if (!proveedores.length) return estadoVacio('usuarios', 'Sin proveedores', 'Registra proveedores para programar recepciones.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Código</th><th>Proveedor</th><th>Contacto</th><th>Teléfono</th><th>Correo</th><th>Estado</th><th></th></tr></thead>
    <tbody>${proveedores.map((proveedor) => `<tr>
      <td class="mono primary-cell">${esc(proveedor.codigo)}</td>
      <td>${esc(proveedor.nombre)}</td><td>${esc(proveedor.contacto || '—')}</td>
      <td>${esc(proveedor.telefono || '—')}</td><td>${esc(proveedor.correo || '—')}</td>
      <td>${proveedor.activo ? '<span class="badge completada">Activo</span>' : '<span class="badge cancelada">Inactivo</span>'}</td>
      <td class="text-right">${puedeOperar() ? `<button class="btn btn-small btn-ghost" type="button" data-editar-proveedor="${proveedor.id}">Editar</button>` : ''}</td>
    </tr>`).join('')}</tbody></table></div>`;
}

function tablaPedidos(pedidos) {
  if (!pedidos.length) return estadoVacio('rutas', 'Sin pedidos', 'Crea un pedido para iniciar picking y empaque.');
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr><th>Folio</th><th>Cliente</th><th>Estado</th><th>Prioridad</th><th>Líneas</th><th>Bultos</th><th>Peso</th><th>Compromiso</th><th></th></tr></thead>
    <tbody>${pedidos.map((pedido) => `<tr>
      <td class="primary-cell mono">${esc(pedido.folio)}</td>
      <td>${esc(pedido.cliente)}<span class="sub">${esc(pedido.cliente_codigo)}</span></td>
      <td>${badgeEstado(pedido.estado)}</td>
      <td>${esc(pedido.prioridad)}</td>
      <td>${numero(pedido.num_lineas)}</td><td>${numero(pedido.num_bultos)}</td>
      <td>${peso(pedido.peso_kg)}</td><td>${esc(fechaCorta(pedido.fecha_compromiso))}</td>
      <td class="text-right nowrap">
        <button class="btn btn-small btn-ghost" type="button" data-ver-pedido="${pedido.id}">Ver</button>
        ${pedido.estado === 'BORRADOR' && puedeOperar() ? `<button class="btn btn-small btn-ghost" type="button" data-editar-pedido="${pedido.id}">Editar</button>` : ''}
        ${['BORRADOR', 'LISTO'].includes(pedido.estado) && puedeOperar() ? `<button class="btn btn-small btn-danger" type="button" data-cancelar-pedido="${pedido.id}">Cancelar</button>` : ''}
      </td>
    </tr>`).join('')}</tbody></table></div>`;
}

/* --------------------------------------------------------------------------
   Formularios de maestros
   -------------------------------------------------------------------------- */
function abrirFormularioCliente(cliente = null) {
  const editando = Boolean(cliente);
  abrirModal({
    titulo: editando ? 'Editar cliente' : 'Nuevo cliente',
    subtitulo: 'Datos usados para consolidar rutas y rastrear entregas.',
    cuerpo: `<form id="formCliente"><div class="form-grid">
      <label class="field"><span>Código *</span><input class="input" id="cliCodigo" maxlength="30" value="${esc(cliente?.codigo || '')}" ${editando ? 'disabled' : ''} placeholder="CD-015" required></label>
      <label class="field"><span>Nombre *</span><input class="input" id="cliNombre" maxlength="150" value="${esc(cliente?.nombre || '')}" placeholder="Cliente nuevo" required></label>
      <label class="field"><span>Tipo de cliente *</span><select class="select" id="cliTipo">${opciones(TIPOS_CLIENTE, cliente?.tipo_cliente || 'MINORISTA')}</select></label>
      <label class="field"><span>Zona *</span><select class="select" id="cliZona">${opciones(ZONAS_CLIENTE, cliente?.zona || 'NORTE')}</select></label>
      <label class="field span-2"><span>Dirección *</span><input class="input" id="cliDireccion" value="${esc(cliente?.direccion || '')}" placeholder="Calle, número, colonia" required></label>
      <label class="field"><span>Colonia</span><input class="input" id="cliColonia" value="${esc(cliente?.colonia || '')}"></label>
      <label class="field"><span>Teléfono</span><input class="input" id="cliTelefono" value="${esc(cliente?.telefono || '')}"></label>
      <label class="field"><span>Contacto</span><input class="input" id="cliContacto" value="${esc(cliente?.contacto || '')}"></label>
      <label class="field"><span>Latitud *</span><input class="input" id="cliLat" type="number" step="0.000001" value="${esc(cliente?.latitud ?? 25.6866)}" required></label>
      <label class="field"><span>Longitud *</span><input class="input" id="cliLon" type="number" step="0.000001" value="${esc(cliente?.longitud ?? -100.3161)}" required></label>
      ${editando ? `<label class="check-row span-2"><input type="checkbox" id="cliActivo" ${cliente.activo ? 'checked' : ''}><span>Cliente activo</span></label>` : ''}
    </div><p class="form-error" id="errorCliente"></p></form>`,
    acciones: `<button class="btn btn-ghost" type="button" id="cancelarCliente">Cancelar</button><button class="btn btn-primary" type="button" id="guardarCliente">${editando ? 'Guardar cambios' : 'Crear cliente'}</button>`,
  });
  $('#cancelarCliente').onclick = cerrarModal;
  $('#guardarCliente').onclick = () => {
    const payload = {
      nombre: $('#cliNombre').value.trim(), tipo_cliente: $('#cliTipo').value,
      zona: $('#cliZona').value, direccion: $('#cliDireccion').value.trim(),
      colonia: $('#cliColonia').value.trim() || null, telefono: $('#cliTelefono').value.trim() || null,
      contacto: $('#cliContacto').value.trim() || null, latitud: Number($('#cliLat').value),
      longitud: Number($('#cliLon').value),
    };
    if (editando) payload.activo = $('#cliActivo').checked;
    else payload.codigo = $('#cliCodigo').value.trim();
    enviarFormulario($('#guardarCliente'), $('#errorCliente'), () => api(
      editando ? `/maestros/clientes/${cliente.id}` : '/maestros/clientes',
      { method: editando ? 'PATCH' : 'POST', body: JSON.stringify(payload) },
    ), editando ? 'Cliente actualizado.' : 'Cliente creado.');
  };
}

function abrirFormularioProducto(producto = null) {
  const editando = Boolean(producto);
  abrirModal({
    titulo: editando ? 'Editar producto' : 'Nuevo producto',
    subtitulo: 'Peso y volumen unitarios se usan para capacidad de vehículos y etiquetas.',
    cuerpo: `<form id="formProducto"><div class="form-grid">
      <label class="field"><span>SKU *</span><input class="input" id="proSku" maxlength="50" value="${esc(producto?.sku || '')}" ${editando ? 'disabled' : ''} required></label>
      <label class="field"><span>Nombre *</span><input class="input" id="proNombre" maxlength="150" value="${esc(producto?.nombre || '')}" required></label>
      <label class="field"><span>Stock mínimo *</span><input class="input" id="proMinimo" type="number" min="0" value="${producto?.stock_minimo ?? 5}" required></label>
      <label class="field"><span>Peso unitario (kg) *</span><input class="input" id="proPeso" type="number" min="0.001" step="0.001" value="${producto?.peso_kg ?? 1}" required></label>
      <label class="field"><span>Volumen unitario (m³) *</span><input class="input" id="proVolumen" type="number" min="0.0001" step="0.0001" value="${producto?.volumen_m3 ?? 0.01}" required></label>
      ${editando ? `<label class="check-row"><input type="checkbox" id="proActivo" ${producto.activo ? 'checked' : ''}><span>Producto activo</span></label>` : ''}
    </div><p class="form-error" id="errorProducto"></p></form>`,
    acciones: `<button class="btn btn-ghost" type="button" id="cancelarProducto">Cancelar</button><button class="btn btn-primary" type="button" id="guardarProducto">${editando ? 'Guardar cambios' : 'Crear producto'}</button>`,
  });
  $('#cancelarProducto').onclick = cerrarModal;
  $('#guardarProducto').onclick = () => {
    const payload = {
      nombre: $('#proNombre').value.trim(), stock_minimo: Number($('#proMinimo').value),
      peso_kg: Number($('#proPeso').value), volumen_m3: Number($('#proVolumen').value),
    };
    if (editando) payload.activo = $('#proActivo').checked;
    else payload.sku = $('#proSku').value.trim();
    enviarFormulario($('#guardarProducto'), $('#errorProducto'), () => api(
      editando ? `/maestros/productos/${producto.id}` : '/maestros/productos',
      { method: editando ? 'PATCH' : 'POST', body: JSON.stringify(payload) },
    ), editando ? 'Producto actualizado.' : 'Producto creado.');
  };
}

function abrirFormularioUbicacion(ubicacion = null) {
  const editando = Boolean(ubicacion);
  abrirModal({
    titulo: editando ? 'Editar ubicación' : 'Nueva ubicación',
    subtitulo: 'Define pasillo, rack, nivel y zona operativa.',
    cuerpo: `<form id="formUbicacion"><div class="form-grid">
      <label class="field"><span>Código *</span><input class="input" id="ubiCodigo" maxlength="30" value="${esc(ubicacion?.codigo || '')}" ${editando ? 'disabled' : ''} placeholder="E-01-1" required></label>
      <label class="field"><span>Pasillo *</span><input class="input" id="ubiPasillo" maxlength="10" value="${esc(ubicacion?.pasillo || '')}" required></label>
      <label class="field"><span>Rack *</span><input class="input" id="ubiRack" maxlength="10" value="${esc(ubicacion?.rack || '')}" required></label>
      <label class="field"><span>Nivel *</span><input class="input" id="ubiNivel" type="number" min="1" value="${ubicacion?.nivel ?? 1}" required></label>
      <label class="field"><span>Orden de picking *</span><input class="input" id="ubiOrden" type="number" min="0" value="${ubicacion?.orden_picking ?? 999}" required></label>
      <label class="field"><span>Tipo de zona *</span><select class="select" id="ubiZona">${opciones(TIPOS_ZONA, ubicacion?.tipo_zona || 'GENERAL')}</select></label>
      ${editando ? `<label class="check-row"><input type="checkbox" id="ubiActivo" ${ubicacion.activo ? 'checked' : ''}><span>Ubicación activa</span></label>` : ''}
    </div><p class="form-error" id="errorUbicacion"></p></form>`,
    acciones: `<button class="btn btn-ghost" type="button" id="cancelarUbicacion">Cancelar</button><button class="btn btn-primary" type="button" id="guardarUbicacion">${editando ? 'Guardar cambios' : 'Crear ubicación'}</button>`,
  });
  $('#cancelarUbicacion').onclick = cerrarModal;
  $('#guardarUbicacion').onclick = () => {
    const payload = {
      pasillo: $('#ubiPasillo').value.trim().toUpperCase(), rack: $('#ubiRack').value.trim(),
      nivel: Number($('#ubiNivel').value), orden_picking: Number($('#ubiOrden').value),
      tipo_zona: $('#ubiZona').value,
    };
    if (editando) payload.activo = $('#ubiActivo').checked;
    else payload.codigo = $('#ubiCodigo').value.trim();
    enviarFormulario($('#guardarUbicacion'), $('#errorUbicacion'), () => api(
      editando ? `/maestros/ubicaciones/${ubicacion.id}` : '/maestros/ubicaciones',
      { method: editando ? 'PATCH' : 'POST', body: JSON.stringify(payload) },
    ), editando ? 'Ubicación actualizada.' : 'Ubicación creada.');
  };
}

function abrirFormularioLote(lote = null) {
  const datos = estado.maestrosDatos || {};
  const editando = Boolean(lote);
  abrirModal({
    titulo: editando ? 'Editar lote' : 'Nuevo lote',
    subtitulo: 'La recepción es la vía recomendada para ingresar stock; este formulario mantiene el catálogo de lotes.',
    cuerpo: `<form id="formLote"><div class="form-grid">
      <label class="field"><span>Producto *</span><select class="select" id="lotProducto" ${editando ? 'disabled' : ''}>${opcionesProductos(datos.productos || [], lote?.producto_id)}</select></label>
      <label class="field"><span>Ubicación *</span><select class="select" id="lotUbicacion">${opcionesUbicaciones(datos.ubicaciones || [], lote?.id ? undefined : null)}</select></label>
      <label class="field"><span>Lote *</span><input class="input" id="lotCodigo" maxlength="50" value="${esc(lote?.lote || '')}" ${editando ? 'disabled' : ''} placeholder="LOTE-2026-01" required></label>
      <label class="field"><span>Caducidad</span><input class="input" id="lotCaducidad" type="date" value="${esc(lote?.caducidad || '')}"></label>
      <label class="field"><span>Cantidad *</span><input class="input" id="lotCantidad" type="number" min="0" value="${lote?.cantidad ?? 0}" required></label>
      <label class="field"><span>Condición *</span><select class="select" id="lotCondicion">${opciones(CONDICIONES_LOTE, lote?.condicion || 'BUENO')}</select></label>
    </div><p class="form-error" id="errorLote"></p></form>`,
    acciones: `<button class="btn btn-ghost" type="button" id="cancelarLote">Cancelar</button><button class="btn btn-primary" type="button" id="guardarLote">${editando ? 'Guardar cambios' : 'Crear lote'}</button>`,
  });
  if (editando) {
    $('#lotUbicacion').value = [...$('#lotUbicacion').options].find((opcion) => opcion.textContent.includes(lote.ubicacion))?.value || $('#lotUbicacion').value;
  }
  $('#cancelarLote').onclick = cerrarModal;
  $('#guardarLote').onclick = () => {
    const payload = {
      ubicacion_id: Number($('#lotUbicacion').value),
      caducidad: $('#lotCaducidad').value || null,
      cantidad: Number($('#lotCantidad').value), condicion: $('#lotCondicion').value,
    };
    if (!editando) {
      payload.producto_id = Number($('#lotProducto').value);
      payload.lote = $('#lotCodigo').value.trim();
    }
    enviarFormulario($('#guardarLote'), $('#errorLote'), () => api(
      editando ? `/maestros/lotes/${lote.id}` : '/maestros/lotes',
      { method: editando ? 'PATCH' : 'POST', body: JSON.stringify(payload) },
    ), editando ? 'Lote actualizado.' : 'Lote creado.');
  };
}

function abrirFormularioProveedor(proveedor = null) {
  const editando = Boolean(proveedor);
  abrirModal({
    titulo: editando ? 'Editar proveedor' : 'Nuevo proveedor',
    subtitulo: 'Se usa para programar citas y órdenes de compra.',
    cuerpo: `<form id="formProveedor"><div class="form-grid">
      <label class="field"><span>Código *</span><input class="input" id="prvCodigo" maxlength="30" value="${esc(proveedor?.codigo || '')}" ${editando ? 'disabled' : ''} placeholder="PROV-004" required></label>
      <label class="field"><span>Nombre *</span><input class="input" id="prvNombre" maxlength="150" value="${esc(proveedor?.nombre || '')}" required></label>
      <label class="field"><span>Contacto</span><input class="input" id="prvContacto" maxlength="120" value="${esc(proveedor?.contacto || '')}"></label>
      <label class="field"><span>Teléfono</span><input class="input" id="prvTelefono" maxlength="30" value="${esc(proveedor?.telefono || '')}"></label>
      <label class="field span-2"><span>Correo</span><input class="input" id="prvCorreo" type="email" maxlength="160" value="${esc(proveedor?.correo || '')}"></label>
      ${editando ? `<label class="check-row"><input type="checkbox" id="prvActivo" ${proveedor.activo ? 'checked' : ''}><span>Proveedor activo</span></label>` : ''}
    </div><p class="form-error" id="errorProveedor"></p></form>`,
    acciones: `<button class="btn btn-ghost" type="button" id="cancelarProveedor">Cancelar</button><button class="btn btn-primary" type="button" id="guardarProveedor">${editando ? 'Guardar cambios' : 'Crear proveedor'}</button>`,
  });
  $('#cancelarProveedor').onclick = cerrarModal;
  $('#guardarProveedor').onclick = () => {
    const payload = {
      nombre: $('#prvNombre').value.trim(), contacto: $('#prvContacto').value.trim() || null,
      telefono: $('#prvTelefono').value.trim() || null, correo: $('#prvCorreo').value.trim() || null,
    };
    if (editando) payload.activo = $('#prvActivo').checked;
    else payload.codigo = $('#prvCodigo').value.trim();
    enviarFormulario($('#guardarProveedor'), $('#errorProveedor'), () => api(
      editando ? `/maestros/proveedores/${proveedor.id}` : '/maestros/proveedores',
      { method: editando ? 'PATCH' : 'POST', body: JSON.stringify(payload) },
    ), editando ? 'Proveedor actualizado.' : 'Proveedor creado.');
  };
}

async function abrirEditarPedido(pedidoId) {
  try {
    const detalle = await api(`/maestros/pedidos/${pedidoId}`);
    abrirFormularioPedido(detalle);
  } catch (error) {
    toast(error.message, 'error');
  }
}

function abrirFormularioPedido(pedido = null) {
  const datos = estado.maestrosDatos || {};
  const editando = Boolean(pedido);
  const clientes = datos.clientes || [];
  const productos = datos.productos || [];
  if (!clientes.length || !productos.length) {
    toast('Necesitas al menos un cliente y un producto para crear pedidos.', 'error');
    return;
  }
  const cuerpo = `<form id="formPedido">
    <div class="form-grid">
      <label class="field"><span>Cliente *</span><select class="select" id="pedCliente">${opcionesClientes(clientes, pedido?.id ? pedido.cliente_id : null)}</select></label>
      <label class="field"><span>Prioridad *</span><select class="select" id="pedPrioridad">${opciones(['NORMAL', 'ALTA'], pedido?.prioridad || 'NORMAL')}</select></label>
      <label class="field"><span>Fecha compromiso</span><input class="input" id="pedFecha" type="date" value="${esc(pedido?.fecha_compromiso || mananaISO())}"></label>
      <label class="field span-2"><span>Observaciones</span><input class="input" id="pedObservaciones" value="${esc(pedido?.observaciones || '')}" placeholder="Notas de preparación"></label>
    </div>
    <div class="detail-block" style="margin-top:14px">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px">
        <h3 style="margin:0">Líneas del pedido</h3>
        <button class="btn btn-small btn-ghost" type="button" id="agregarLineaPedido">${ico('mas')} Agregar línea</button>
      </div>
      <div class="line-editor" id="lineasPedido"></div>
    </div>
    <p class="form-error" id="errorPedido"></p>
  </form>`;
  abrirModal({
    titulo: editando ? `Editar ${pedido.folio}` : 'Nuevo pedido',
    subtitulo: 'El pedido nace en BORRADOR; luego pasa por picking, empaque y QC antes de rutas.',
    cuerpo,
    acciones: `<button class="btn btn-ghost" type="button" id="cancelarPedido">Cancelar</button><button class="btn btn-primary" type="button" id="guardarPedido">${editando ? 'Guardar cambios' : 'Crear pedido'}</button>`,
  });
  const contenedor = $('#lineasPedido');
  const lineas = editando ? (pedido.lineas || []).map((linea) => [linea.producto_id, linea.cantidad]) : [[null, 1]];
  lineas.forEach(([productoId, cantidad]) => agregarFilaLinea(contenedor, productos, productoId, cantidad));
  $('#agregarLineaPedido').onclick = () => agregarFilaLinea(contenedor, productos);
  $('#cancelarPedido').onclick = cerrarModal;
  $('#guardarPedido').onclick = () => {
    const body = {
      cliente_id: Number($('#pedCliente').value), prioridad: $('#pedPrioridad').value,
      fecha_compromiso: $('#pedFecha').value || null,
      observaciones: $('#pedObservaciones').value.trim() || null,
      lineas: leerLineasEditor(contenedor),
    };
    if (!body.lineas.length) {
      $('#errorPedido').textContent = 'Agrega al menos una línea con producto y cantidad.';
      return;
    }
    enviarFormulario($('#guardarPedido'), $('#errorPedido'), () => api(
      editando ? `/maestros/pedidos/${pedido.id}` : '/maestros/pedidos',
      { method: editando ? 'PATCH' : 'POST', body: JSON.stringify(body) },
    ), editando ? 'Pedido actualizado.' : 'Pedido creado. Ahora puedes generar la ola de picking.');
  };
}

async function verPedidoMaestro(pedido) {
  try {
    const detalle = await api(`/maestros/pedidos/${pedido.id}`);
    const lineas = (detalle.lineas || []).map((linea) => `<tr>
      <td class="mono">${esc(linea.sku)}</td><td class="primary-cell">${esc(linea.producto)}</td>
      <td>${numero(linea.cantidad)}</td><td>${peso(linea.peso_kg)}</td><td>${volumen(linea.volumen_m3)}</td>
    </tr>`).join('');
    abrirModal({
      titulo: detalle.folio,
      subtitulo: `${detalle.cliente} · ${detalle.estado} · ${fechaCorta(detalle.fecha_compromiso)}`,
      cuerpo: `<div class="operation-summary"><span>Líneas <strong>${numero(detalle.num_lineas)}</strong></span><span>Bultos <strong>${numero(detalle.num_bultos)}</strong></span><span>Peso <strong>${peso(detalle.peso_kg)}</strong></span><span>Volumen <strong>${volumen(detalle.volumen_m3)}</strong></span></div>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>SKU</th><th>Producto</th><th>Cantidad</th><th>Peso</th><th>Volumen</th></tr></thead><tbody>${lineas || '<tr><td colspan="5">Sin líneas</td></tr>'}</tbody></table></div>`,
      acciones: `<button class="btn btn-ghost" type="button" id="cerrarPedido">Cerrar</button>${detalle.estado === 'BORRADOR' && puedeOperar() ? `<button class="btn btn-primary" type="button" id="editarPedidoDetalle">Editar pedido</button>` : ''}`,
    });
    $('#cerrarPedido').onclick = cerrarModal;
    $('#editarPedidoDetalle')?.addEventListener('click', () => abrirFormularioPedido(detalle));
  } catch (error) { toast(error.message, 'error'); }
}

/* --------------------------------------------------------------------------
   Recepción
   -------------------------------------------------------------------------- */
PAGINAS.recepcion = async function (version) {
  const [ordenes, incidencias, proveedores, productos, ubicaciones] = await Promise.all([
    api('/recepcion/ordenes'),
    api('/recepcion/incidencias'),
    api('/maestros/proveedores'),
    api('/maestros/productos'),
    api('/maestros/ubicaciones'),
  ]);
  if (!vigente(version)) return;
  estado.recepcionDatos = { ordenes, incidencias, proveedores, productos, ubicaciones };
  renderPaginaRecepcion();
};

function renderPaginaRecepcion() {
  const datos = estado.recepcionDatos || {};
  const ordenes = datos.ordenes || [];
  const incidencias = datos.incidencias || [];
  const pendientes = ordenes.filter((orden) => ['PROGRAMADA', 'EN_RECEPCION'].includes(orden.estado)).length;
  const recibidas = ordenes.filter((orden) => ['RECIBIDA', 'CON_INCIDENCIA'].includes(orden.estado)).length;
  const totalRecibido = ordenes.reduce((total, orden) => total + Number(orden.total_recibido || 0), 0);

  const filas = ordenes.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Folio</th><th>Proveedor</th><th>Cita</th><th>Andén</th><th>Solicitado</th><th>Recibido</th><th>Estado</th><th></th></tr></thead>
        <tbody>${ordenes.map((orden) => `<tr>
          <td class="primary-cell mono">${esc(orden.folio)}</td>
          <td>${esc(orden.proveedor)}</td>
          <td>${esc(fechaCorta(orden.fecha_esperada))}<span class="sub">${esc((orden.hora_estimada || '').slice(0, 5) || 'Sin hora')}</span></td>
          <td>${esc(orden.anden || '—')}</td>
          <td>${numero(orden.total_solicitado)}</td><td>${numero(orden.total_recibido)}</td>
          <td>${badgeEstado(orden.estado)}</td>
          <td class="text-right nowrap">
            ${['PROGRAMADA', 'EN_RECEPCION', 'CON_INCIDENCIA'].includes(orden.estado) && puedeOperar() ? `<button class="btn btn-small btn-success" type="button" data-recibir-oc="${orden.id}">Recibir</button>` : ''}
            <button class="btn btn-small btn-ghost" type="button" data-ver-oc="${orden.id}">Ver</button>
            ${['PROGRAMADA', 'EN_RECEPCION'].includes(orden.estado) && puedeOperar() ? `<button class="btn btn-small btn-danger" type="button" data-cancelar-oc="${orden.id}">Cancelar</button>` : ''}
          </td>
        </tr>`).join('')}</tbody></table></div>`
    : estadoVacio('paquete', 'Sin órdenes de compra', 'Programa la primera cita de recepción.');

  const filasIncidencias = incidencias.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Fecha</th><th>OC</th><th>Proveedor</th><th>Producto</th><th>Descripción</th><th>Responsable</th><th></th></tr></thead>
        <tbody>${incidencias.map((item) => `<tr>
          <td class="nowrap">${esc(fechaHora(item.fecha))}</td><td class="mono">${esc(item.orden_folio)}</td>
          <td>${esc(item.proveedor)}</td><td>${esc(item.producto || '—')}</td>
          <td class="primary-cell">${esc(item.descripcion)}<span class="sub">${esc(item.comentario || '')}</span></td>
          <td>${esc(item.responsable || '—')}</td>
          <td class="text-right">${item.foto_url ? `<button class="btn btn-small btn-ghost" type="button" data-foto-incidencia="${esc(item.foto_url)}">${ico('camara')} Foto</button>` : ''}</td>
        </tr>`).join('')}</tbody></table></div>`
    : estadoVacio('check', 'Sin incidencias', 'Las recepciones con daños o diferencias aparecerán aquí.');

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div><p class="eyebrow">Entrada de mercancía</p><h1>Recepción y citas</h1><p class="muted">Programa proveedores, valida cantidades, captura lote/caducidad y registra incidencias con foto.</p></div>
      ${puedeOperar() ? `<div class="page-head-actions"><button class="btn btn-primary" type="button" id="nuevaOC">${ico('mas')} Nueva OC / cita</button></div>` : ''}
    </div>
    <div class="grid grid-kpi">
      ${kpiCard({ clase: 'orange', icono: 'calendario', etiqueta: 'Citas pendientes', valor: numero(pendientes), detalle: 'programadas o en recepción' })}
      ${kpiCard({ clase: 'green', icono: 'check', etiqueta: 'Recepciones cerradas', valor: numero(recibidas), detalle: 'recibidas o con incidencia' })}
      ${kpiCard({ clase: 'blue', icono: 'paquete', etiqueta: 'Unidades recibidas', valor: numero(totalRecibido), detalle: 'acumulado de las OC listadas' })}
      ${kpiCard({ clase: 'red', icono: 'alerta', etiqueta: 'Incidencias', valor: numero(incidencias.length), detalle: 'con evidencia y responsable' })}
    </div>
    <section class="panel panel-pad section-gap">${encabezadoPanel('Citas y órdenes de compra', 'Control de proveedor, hora, andén y cantidades.')}${filas}</section>
    <section class="panel panel-pad section-gap">${encabezadoPanel('Incidencias de recepción', 'Mercancía dañada, faltante o diferencia contra la OC.')}${filasIncidencias}</section>`;

  $('#nuevaOC')?.addEventListener('click', abrirNuevaOC);
  $$('[data-recibir-oc]').forEach((boton) => boton.addEventListener('click', () => abrirRecibirOC(Number(boton.dataset.recibirOc))));
  $$('[data-ver-oc]').forEach((boton) => boton.addEventListener('click', () => verOC(Number(boton.dataset.verOc))));
  $$('[data-cancelar-oc]').forEach((boton) => boton.addEventListener('click', () => cancelarOC(Number(boton.dataset.cancelarOc))));
  $$('[data-foto-incidencia]').forEach((boton) => boton.addEventListener('click', () => verEvidencia(boton.dataset.fotoIncidencia, 'Incidencia de recepción')));
}

function abrirNuevaOC() {
  const datos = estado.recepcionDatos || {};
  const proveedores = datos.proveedores || [];
  const productos = datos.productos || [];
  if (!proveedores.length || !productos.length) {
    toast('Necesitas proveedores y productos para crear una OC.', 'error');
    return;
  }
  abrirModal({
    titulo: 'Programar cita / orden de compra',
    subtitulo: 'Registra proveedor, fecha, hora, andén y productos esperados.',
    cuerpo: `<form id="formOC"><div class="form-grid">
      <label class="field"><span>Proveedor *</span><select class="select" id="ocProveedor">${proveedores.map((p) => `<option value="${p.id}">${esc(p.nombre)} · ${esc(p.codigo)}</option>`).join('')}</select></label>
      <label class="field"><span>Fecha esperada *</span><input class="input" id="ocFecha" type="date" value="${hoyISO()}" required></label>
      <label class="field"><span>Hora estimada</span><input class="input" id="ocHora" type="time" value="09:00"></label>
      <label class="field"><span>Andén / rampa</span><input class="input" id="ocAnden" maxlength="20" placeholder="A-1"></label>
      <label class="field span-2"><span>Observaciones</span><input class="input" id="ocObservaciones" placeholder="Instrucciones de descarga"></label>
    </div><div class="detail-block" style="margin-top:14px"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px"><h3 style="margin:0">Productos esperados</h3><button class="btn btn-small btn-ghost" type="button" id="agregarLineaOC">${ico('mas')} Agregar línea</button></div><div class="line-editor" id="lineasOC"></div></div><p class="form-error" id="errorOC"></p></form>`,
    acciones: `<button class="btn btn-ghost" type="button" id="cancelarOC">Cancelar</button><button class="btn btn-primary" type="button" id="guardarOC">Programar OC</button>`,
    ancho: 'wide',
  });
  const contenedor = $('#lineasOC');
  agregarFilaLinea(contenedor, productos);
  $('#agregarLineaOC').onclick = () => agregarFilaLinea(contenedor, productos);
  $('#cancelarOC').onclick = cerrarModal;
  $('#guardarOC').onclick = () => {
    const lineas = leerLineasEditor(contenedor).map((linea) => ({
      producto_id: linea.producto_id, cantidad_solicitada: linea.cantidad,
    }));
    if (!lineas.length) { $('#errorOC').textContent = 'Agrega al menos una línea.'; return; }
    enviarFormulario($('#guardarOC'), $('#errorOC'), () => api('/recepcion/ordenes', {
      method: 'POST',
      body: JSON.stringify({
        proveedor_id: Number($('#ocProveedor').value), fecha_esperada: $('#ocFecha').value,
        hora_estimada: $('#ocHora').value || null, anden: $('#ocAnden').value.trim() || null,
        observaciones: $('#ocObservaciones').value.trim() || null, lineas,
      }),
    }), 'Orden de compra programada.');
  };
}

async function abrirRecibirOC(ordenId) {
  try {
    const orden = await api(`/recepcion/ordenes/${ordenId}`);
    const datos = estado.recepcionDatos || {};
    const ubicaciones = (datos.ubicaciones || []).filter((u) => u.activo);
    const filas = orden.lineas.map((linea) => {
      const pendiente = Math.max(0, Number(linea.cantidad_solicitada) - Number(linea.cantidad_recibida));
      return `<tr data-linea-oc="${linea.id}" data-producto="${linea.producto_id}">
        <td class="primary-cell">${esc(linea.producto)}<span class="sub">${esc(linea.sku)}</span></td>
        <td>${numero(linea.cantidad_solicitada)}</td><td>${numero(linea.cantidad_recibida)}</td><td>${numero(pendiente)}</td>
        <td><input class="input rec-cantidad" type="number" min="0" max="${pendiente}" value="${pendiente}" ${pendiente === 0 ? 'disabled' : ''}></td>
        <td><input class="input rec-lote" maxlength="50" placeholder="Lote"></td>
        <td><input class="input rec-caducidad" type="date"></td>
        <td><select class="select rec-condicion">${opciones(CONDICIONES_LOTE, 'BUENO')}</select></td>
        <td><div style="display:flex;gap:5px"><select class="select rec-ubicacion">${opcionesUbicaciones(ubicaciones, null)}</select><button class="btn btn-small btn-ghost" type="button" data-sugerir="${linea.producto_id}">Sugerir</button></div></td>
      </tr>`;
    }).join('');
    abrirModal({
      titulo: `Recibir ${orden.folio}`,
      subtitulo: `${orden.proveedor} · andén ${orden.anden || 'sin asignar'} · ${fechaCorta(orden.fecha_esperada)}`,
      cuerpo: `<form id="formRecepcion">
        <p class="inline-note">Captura cantidad, lote, caducidad, condición y ubicación de cada línea. Si hay daño, registra la incidencia y adjunta foto.</p>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Producto</th><th>Solicitado</th><th>Recibido</th><th>Pendiente</th><th>Cantidad a recibir</th><th>Lote</th><th>Caducidad</th><th>Condición</th><th>Destino / putaway</th></tr></thead><tbody>${filas}</tbody></table></div>
        <label class="check-row" style="margin-top:12px"><input type="checkbox" id="hayIncidencia"><span>Registrar incidencia de recepción</span></label>
        <div id="bloqueIncidencia" class="conditional"><div class="form-grid"><label class="field span-2"><span>Descripción *</span><input class="input" id="incDescripcion" placeholder="Caja rota, producto incorrecto, faltante…"></label><label class="field span-2"><span>Comentario</span><textarea class="textarea" id="incComentario" placeholder="Detalle para reclamación al proveedor"></textarea></label><label class="field span-2"><span>Fotografía</span><span class="file-drop">${ico('camara')} Adjuntar foto<input type="file" id="incFoto" accept="image/png,image/jpeg"></span></label></div></div>
        <p class="form-error" id="errorRecepcion"></p>
      </form>`,
      acciones: `<button class="btn btn-ghost" type="button" id="cancelarRecepcion">Cancelar</button><button class="btn btn-success" type="button" id="guardarRecepcion">${ico('check')} Confirmar recepción</button>`,
      ancho: 'wide',
    });
    $('#hayIncidencia').onchange = (evento) => $('#bloqueIncidencia').classList.toggle('visible', evento.target.checked);
    $('#cancelarRecepcion').onclick = cerrarModal;
    $$('[data-sugerir]').forEach((boton) => boton.addEventListener('click', async () => {
      try {
        const sugerida = await api(`/recepcion/sugerir-ubicacion?producto_id=${boton.dataset.sugerir}`);
        const select = boton.closest('tr').querySelector('.rec-ubicacion');
        select.value = String(sugerida.id);
        toast(`Ubicación sugerida: ${sugerida.codigo}`, 'info');
      } catch (error) { toast(error.message, 'error'); }
    }));
    $('#guardarRecepcion').onclick = async () => {
      const errorBox = $('#errorRecepcion');
      errorBox.textContent = '';
      const lineas = [...$('#formRecepcion').querySelectorAll('[data-linea-oc]')]
        .map((fila) => ({
          linea_id: Number(fila.dataset.lineaOc),
          producto_id: Number(fila.dataset.producto),
          cantidad_recibida: Number(fila.querySelector('.rec-cantidad').value),
          lote: fila.querySelector('.rec-lote').value.trim() || null,
          caducidad: fila.querySelector('.rec-caducidad').value || null,
          condicion: fila.querySelector('.rec-condicion').value,
          ubicacion_id: Number(fila.querySelector('.rec-ubicacion').value),
        }))
        .filter((linea) => linea.cantidad_recibida > 0);
      if (!lineas.length) { errorBox.textContent = 'Registra al menos una cantidad recibida.'; return; }
      let incidencia = null;
      if ($('#hayIncidencia').checked) {
        const descripcion = $('#incDescripcion').value.trim();
        if (!descripcion) { errorBox.textContent = 'Describe la incidencia.'; return; }
        const archivo = $('#incFoto').files?.[0];
        incidencia = {
          descripcion, comentario: $('#incComentario').value.trim() || null,
          producto_id: lineas[0].producto_id || null,
          foto_base64: archivo ? await leerArchivoBase64(archivo) : null,
        };
      }
      const boton = $('#guardarRecepcion');
      const restaurar = bloquear(boton, 'Recibiendo…');
      try {
        await api(`/recepcion/ordenes/${orden.id}/recibir`, {
          method: 'POST',
          body: JSON.stringify({ observaciones: null, lineas, incidencia }),
        });
        toast('Recepción registrada y stock actualizado.', 'success');
        cerrarModal(); renderSeccion();
      } catch (error) { errorBox.textContent = error.message; toast(error.message, 'error'); restaurar(); }
    };
  } catch (error) { toast(error.message, 'error'); }
}

async function verOC(ordenId) {
  try {
    const orden = await api(`/recepcion/ordenes/${ordenId}`);
    const lineas = orden.lineas.map((linea) => `<tr>
      <td class="mono">${esc(linea.sku)}</td><td class="primary-cell">${esc(linea.producto)}</td>
      <td>${numero(linea.cantidad_solicitada)}</td><td>${numero(linea.cantidad_recibida)}</td>
      <td>${numero(Number(linea.cantidad_solicitada) - Number(linea.cantidad_recibida))}</td>
    </tr>`).join('');
    abrirModal({
      titulo: orden.folio,
      subtitulo: `${orden.proveedor} · ${orden.estado} · andén ${orden.anden || '—'}`,
      cuerpo: `<div class="operation-summary"><span>Fecha <strong>${esc(fechaCorta(orden.fecha_esperada))}</strong></span><span>Hora <strong>${esc((orden.hora_estimada || '').slice(0, 5) || '—')}</strong></span><span>Solicitado <strong>${numero(orden.total_solicitado)}</strong></span><span>Recibido <strong>${numero(orden.total_recibido)}</strong></span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>SKU</th><th>Producto</th><th>Solicitado</th><th>Recibido</th><th>Pendiente</th></tr></thead><tbody>${lineas}</tbody></table></div>`,
      acciones: `<button class="btn btn-ghost" type="button" id="cerrarOC">Cerrar</button>`,
    });
    $('#cerrarOC').onclick = cerrarModal;
  } catch (error) { toast(error.message, 'error'); }
}

function cancelarOC(ordenId) {
  if (!window.confirm('¿Cancelar esta cita/orden de compra?')) return;
  api(`/recepcion/ordenes/${ordenId}/cancelar`, { method: 'POST' })
    .then(() => { toast('Orden cancelada.', 'success'); renderSeccion(); })
    .catch((error) => toast(error.message, 'error'));
}

/* --------------------------------------------------------------------------
   Picking / packing
   -------------------------------------------------------------------------- */
PAGINAS.picking = async function (version) {
  const pedidos = await api('/picking/pedidos?limite=100');
  if (!vigente(version)) return;
  estado.pickingDatos = pedidos;
  renderPaginaPicking();
};

function renderPaginaPicking() {
  const pedidos = estado.pickingDatos || [];
  const borradores = pedidos.filter((pedido) => pedido.estado === 'BORRADOR').length;
  const enPicking = pedidos.filter((pedido) => pedido.estado === 'EN_PICKING').length;
  const enEmpaque = pedidos.filter((pedido) => pedido.estado === 'EMPACADO').length;
  const listos = pedidos.filter((pedido) => pedido.estado === 'LISTO').length;
  const tareasPendientes = pedidos.reduce((total, pedido) => total + (pedido.tareas || []).filter((tarea) => tarea.estado === 'PENDIENTE').length, 0);

  const filas = pedidos.length
    ? `<div class="table-wrap"><table class="data-table">
        <thead><tr><th>Pedido</th><th>Cliente</th><th>Estado</th><th>Líneas</th><th>Picking</th><th>Bultos</th><th>Empaque</th><th></th></tr></thead>
        <tbody>${pedidos.map((pedido) => {
          const tareas = pedido.tareas || [];
          const pickeadas = tareas.filter((tarea) => tarea.estado === 'PICKEADO').length;
          const progreso = tareas.length ? `${pickeadas}/${tareas.length}` : '—';
          const acciones = [];
          if (pedido.estado === 'EN_PICKING') acciones.push(`<button class="btn btn-small ${puedeOperar() ? 'btn-success' : 'btn-ghost'}" type="button" data-tareas="${pedido.id}">${puedeOperar() ? 'Surtir' : 'Ver tareas'}</button>`);
          if (pedido.estado === 'PICKING_COMPLETO' && puedeOperar()) acciones.push(`<button class="btn btn-small btn-primary" type="button" data-empacar="${pedido.id}">Empacar</button>`);
          if (pedido.estado === 'EMPACADO') {
            if (puedeOperar()) acciones.push(`<button class="btn btn-small btn-success" type="button" data-aprobar="${pedido.id}">Aprobar QC</button>`);
            acciones.push(`<button class="btn btn-small btn-ghost" type="button" data-etiquetas="${pedido.id}">Etiquetas</button>`);
          }
          if (pedido.estado === 'LISTO' && pedido.bultos?.length) acciones.push(`<button class="btn btn-small btn-ghost" type="button" data-etiquetas="${pedido.id}">Etiquetas</button>`);
          if (pedido.estado === 'BORRADOR') acciones.push('<span class="tiny muted">Pendiente de ola</span>');
          return `<tr>
            <td class="primary-cell mono">${esc(pedido.folio)}<span class="sub">${esc(pedido.prioridad)}</span></td>
            <td>${esc(pedido.cliente)}<span class="sub">${esc(fechaCorta(pedido.fecha_compromiso))}</span></td>
            <td>${badgeEstado(pedido.estado)}</td><td>${numero((pedido.lineas || []).length)}</td>
            <td>${progreso}<span class="sub">${tareasPendientes ? 'tareas pendientes' : 'sin tareas'}</span></td>
            <td>${numero((pedido.bultos || []).length)}</td><td>${pedido.empaque ? esc(pedido.empaque.folio) : '—'}</td>
            <td class="text-right nowrap">${acciones.join('')}</td>
          </tr>`;
        }).join('')}</tbody></table></div>`
    : estadoVacio('inventario', 'Sin pedidos en preparación', 'Crea un pedido en Maestros o revisa los pedidos listos para ruta.');

  $('#appContent').innerHTML = `
    <div class="page-head">
      <div><p class="eyebrow">Preparación de pedidos</p><h1>Picking y packing</h1><p class="muted">Ola de surtido por pasillo, validación de SKU/ubicación, empaque con guías y control de calidad.</p></div>
      ${puedeOperar() ? `<div class="page-head-actions"><button class="btn btn-primary" type="button" id="btnGenerarOla" ${borradores ? '' : 'disabled'} title="${borradores ? 'Generar ola para pedidos BORRADOR' : 'No hay pedidos en BORRADOR'}">${ico('rayo')} Generar ola</button><button class="icon-button" type="button" id="btnRefrescarPicking" title="Actualizar">${ico('refrescar')}</button></div>` : ''}
    </div>
    <div class="grid grid-kpi">
      ${kpiCard({ clase: 'orange', icono: 'inventario', etiqueta: 'En picking', valor: numero(enPicking), detalle: 'pedidos en surtido' })}
      ${kpiCard({ clase: 'blue', icono: 'check', etiqueta: 'Tareas pendientes', valor: numero(tareasPendientes), detalle: 'líneas por surtir' })}
      ${kpiCard({ clase: 'purple', icono: 'paquete', etiqueta: 'En empaque', valor: numero(enEmpaque), detalle: 'esperando QC' })}
      ${kpiCard({ clase: 'green', icono: 'rutas', etiqueta: 'Listos para ruta', valor: numero(listos), detalle: 'aprobados por QC' })}
    </div>
    <div class="operation-summary"><span>BORRADOR <strong>${numero(borradores)}</strong></span><span>En picking <strong>${numero(enPicking)}</strong></span><span>En empaque <strong>${numero(enEmpaque)}</strong></span><span>Listos <strong>${numero(listos)}</strong></span></div>
    <section class="panel panel-pad">${encabezadoPanel('Pedidos en preparación', 'El pedido pasa de BORRADOR a picking, empaque, QC y LISTO.')}${filas}</section>`;

  $('#btnGenerarOla')?.addEventListener('click', generarOlaPicking);
  $('#btnRefrescarPicking')?.addEventListener('click', () => renderSeccion());
  $$('[data-tareas]').forEach((boton) => boton.addEventListener('click', () => abrirTareasPedido(Number(boton.dataset.tareas))));
  $$('[data-empacar]').forEach((boton) => boton.addEventListener('click', () => empacarPedido(Number(boton.dataset.empacar))));
  $$('[data-aprobar]').forEach((boton) => boton.addEventListener('click', () => aprobarPedido(Number(boton.dataset.aprobar))));
  $$('[data-etiquetas]').forEach((boton) => boton.addEventListener('click', () => abrirEtiquetasPedido(Number(boton.dataset.etiquetas))));
}

async function generarOlaPicking() {
  const boton = $('#btnGenerarOla');
  const restaurar = bloquear(boton, 'Generando ola…');
  try {
    const ola = await api('/picking/generar', { method: 'POST', body: JSON.stringify({}) });
    toast(ola.mensaje, 'success', 6000);
    renderSeccion();
  } catch (error) { toast(error.message, 'error', 6500); restaurar(); }
}

async function abrirTareasPedido(pedidoId) {
  try {
    const pedido = await api(`/picking/pedidos/${pedidoId}`);
    const tareas = pedido.tareas || [];
    const filas = tareas.length ? tareas.map((tarea) => `<tr>
      <td><span class="stop-seq">${tarea.orden}</span></td>
      <td class="primary-cell">${esc(tarea.producto)}<span class="sub">${esc(tarea.sku)}</span></td>
      <td class="mono">${esc(tarea.ubicacion)}</td><td>${numero(tarea.cantidad)}</td>
      <td>${badgeEstado(tarea.estado)}</td>
      <td class="text-right">${tarea.estado === 'PENDIENTE' && puedeOperar() ? `<button class="btn btn-small btn-success" type="button" data-confirmar-tarea="${tarea.id}">Surtir</button>` : ''}</td>
    </tr>`).join('') : '<tr><td colspan="6">Sin tareas generadas.</td></tr>';
    abrirModal({
      titulo: `Surtido ${pedido.folio}`,
      subtitulo: `${pedido.cliente} · ${pedido.estado}`,
      ancho: 'wide',
      cuerpo: `<div class="operation-summary"><span>Cliente <strong>${esc(pedido.cliente)}</strong></span><span>Líneas <strong>${numero((pedido.lineas || []).length)}</strong></span><span>Tareas <strong>${numero(tareas.length)}</strong></span><span>Bultos <strong>${numero((pedido.bultos || []).length)}</strong></span></div>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>#</th><th>Producto</th><th>Ubicación</th><th>Cantidad</th><th>Estado</th><th></th></tr></thead><tbody>${filas}</tbody></table></div>`,
      acciones: `<button class="btn btn-ghost" type="button" id="cerrarTareas">Cerrar</button>${pedido.estado === 'PICKING_COMPLETO' && puedeOperar() ? `<button class="btn btn-success" type="button" id="empacarDesdeTareas">Empacar</button>` : ''}`,
    });
    $('#cerrarTareas').onclick = cerrarModal;
    $('#empacarDesdeTareas')?.addEventListener('click', () => empacarPedido(pedido.id));
    $$('[data-confirmar-tarea]').forEach((boton) => boton.addEventListener('click', () => {
      const tarea = tareas.find((item) => item.id === Number(boton.dataset.confirmarTarea));
      if (tarea) abrirConfirmarTarea(pedido, tarea);
    }));
  } catch (error) { toast(error.message, 'error'); }
}

function abrirConfirmarTarea(pedido, tarea) {
  abrirModal({
    titulo: `Surtir ${tarea.sku}`,
    subtitulo: `${pedido.folio} · tarea ${tarea.orden} · ${tarea.producto}`,
    cuerpo: `<p class="inline-note">Escanea el SKU y la ubicación. Si el código no coincide, el sistema rechaza el surtido.</p>
      <div class="operation-summary"><span>Producto <strong>${esc(tarea.producto)}</strong></span><span>Cantidad <strong>${numero(tarea.cantidad)}</strong></span><span>Ubicación <strong>${esc(tarea.ubicacion)}</strong></span></div>
      <div class="task-scan"><label class="field"><span>SKU escaneado *</span><input class="input" id="scanSku" placeholder="${esc(tarea.sku)}" autocomplete="off"></label><label class="field"><span>Ubicación escaneada *</span><input class="input" id="scanUbicacion" placeholder="${esc(tarea.ubicacion)}" autocomplete="off"></label></div>
      <button class="btn-link" type="button" id="usarEscaneoEsperado">Simular escaneo correcto</button><p class="form-error" id="errorScan"></p>`,
    acciones: `<button class="btn btn-ghost" type="button" id="cancelarScan">Cancelar</button><button class="btn btn-success" type="button" id="confirmarScan">Confirmar surtido</button>`,
  });
  $('#usarEscaneoEsperado').onclick = () => { $('#scanSku').value = tarea.sku; $('#scanUbicacion').value = tarea.ubicacion; };
  $('#cancelarScan').onclick = cerrarModal;
  $('#confirmarScan').onclick = async () => {
    const boton = $('#confirmarScan');
    const restaurar = bloquear(boton, 'Validando…');
    try {
      const actualizado = await api(`/picking/tareas/${tarea.id}/confirmar`, {
        method: 'POST',
        body: JSON.stringify({ sku: $('#scanSku').value.trim() || null, ubicacion: $('#scanUbicacion').value.trim() || null }),
      });
      toast('Surtido confirmado.', 'success');
      if ((actualizado.tareas || []).some((item) => item.estado === 'PENDIENTE')) {
        abrirTareasPedido(actualizado.id);
      } else {
        estado.pickingDatos = (estado.pickingDatos || []).map(
          (item) => (item.id === actualizado.id ? actualizado : item),
        );
        cerrarModal();
        toast('Picking completo. El pedido puede empacarse.', 'success', 5000);
        renderPaginaPicking();
      }
    } catch (error) { $('#errorScan').textContent = error.message; toast(error.message, 'error'); restaurar(); }
  };
}

async function empacarPedido(pedidoId) {
  try {
    const pedido = await api(`/picking/pedidos/${pedidoId}/empacar`, { method: 'POST' });
    toast(`Pedido empacado con ${pedido.bultos.length} bulto(s). Revisa las etiquetas.`, 'success', 6000);
    estado.pickingDatos = (estado.pickingDatos || []).map((item) => item.id === pedido.id ? pedido : item);
    renderPaginaPicking();
    abrirEtiquetasPedido(pedido.id);
  } catch (error) { toast(error.message, 'error'); }
}

async function aprobarPedido(pedidoId) {
  try {
    const pedido = await api(`/picking/pedidos/${pedidoId}/aprobar`, { method: 'POST' });
    toast('Control de calidad aprobado. Pedido listo para rutas.', 'success', 6000);
    estado.pickingDatos = (estado.pickingDatos || []).map((item) => item.id === pedido.id ? pedido : item);
    renderPaginaPicking();
    abrirEtiquetasPedido(pedido.id);
  } catch (error) { toast(error.message, 'error'); }
}

async function abrirEtiquetasPedido(pedidoId) {
  try {
    const pedido = await api(`/picking/pedidos/${pedidoId}`);
    const bultos = pedido.bultos || [];
    if (!bultos.length) { toast('El pedido aún no tiene bultos. Primero empaca.', 'info'); return; }
    const etiquetas = bultos.map((bulto, indice) => etiquetaPedido(pedido, bulto, indice + 1, bultos.length)).join('');
    abrirModal({
      titulo: `Etiquetas ${pedido.folio}`,
      subtitulo: `${pedido.cliente} · ${bultos.length} bulto(s) · guía y datos del cliente`, 
      ancho: 'wide',
      cuerpo: `<div class="label-grid">${etiquetas}</div>`,
      acciones: `<button class="btn btn-ghost" type="button" id="cerrarEtiquetas">Cerrar</button><button class="btn btn-primary" type="button" id="imprimirEtiquetas">${ico('descargar')} Imprimir etiquetas</button>`,
    });
    $('#cerrarEtiquetas').onclick = cerrarModal;
    $('#imprimirEtiquetas').onclick = () => imprimirEtiquetas(pedido);
  } catch (error) { toast(error.message, 'error'); }
}

function etiquetaPedido(pedido, bulto, numeroBulto, totalBultos) {
  return `<article class="label-card">
    <div class="label-brand">LogistiXpress · Royal Express</div>
    <h3>${esc(pedido.cliente)}</h3>
    <div>${esc(pedido.direccion)}</div>
    <div class="label-code">${esc(bulto.guia)}</div>
    <div class="barcode"></div>
    <div class="label-meta">
      <div><span>Pedido</span><strong>${esc(pedido.folio)}</strong></div>
      <div><span>Bulto</span><strong>${numeroBulto} / ${totalBultos}</strong></div>
      <div><span>Peso</span><strong>${peso(bulto.peso_kg)}</strong></div>
      <div><span>Volumen</span><strong>${volumen(bulto.volumen_m3)}</strong></div>
      <div><span>Teléfono</span><strong>${esc(pedido.telefono || '—')}</strong></div>
      <div><span>Contenido</span><strong>${esc(bulto.descripcion)}</strong></div>
    </div>
    <div class="label-total">Total de bultos de la entrega: ${numero(totalBultos)}</div>
  </article>`;
}

function imprimirEtiquetas(pedido) {
  const bultos = pedido.bultos || [];
  const ventana = window.open('', '_blank', 'width=780,height=920');
  if (!ventana) { toast('Permite ventanas emergentes para imprimir las etiquetas.', 'error'); return; }
  const etiquetas = bultos.map((bulto, indice) => etiquetaPedido(pedido, bulto, indice + 1, bultos.length)).join('');
  ventana.document.write(`<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Etiquetas ${esc(pedido.folio)}</title><style>
    body{font-family:Inter,Arial,sans-serif;margin:14px;background:#fff;color:#0b1a2c}.label-card{background:#fff;color:#0b1a2c;border:1px solid #cfd8e3;border-radius:8px;padding:14px;margin-bottom:12px;page-break-inside:avoid}.label-brand{font-size:9px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#ff6a00}.label-card h3{margin:4px 0 2px;font-size:16px}.label-code{font-family:ui-monospace,monospace;font-size:20px;font-weight:800;letter-spacing:.03em}.barcode{height:46px;margin:8px 0 2px;background:repeating-linear-gradient(90deg,#111 0 2px,#fff 2px 3px,#111 3px 6px,#fff 6px 9px,#111 9px 10px,#fff 10px 13px)}.label-meta{display:grid;grid-template-columns:1fr 1fr;gap:3px 10px;margin-top:6px}.label-meta span{display:block;color:#5b6b7c;font-size:9px;text-transform:uppercase}.label-meta strong{display:block;color:#142433;font-size:11px}.label-total{color:#5b6b7c;font-size:9px;margin-top:6px}@media print{body{margin:0}.label-card{border:1px dashed #999;margin:6mm}}
  </style></head><body>${etiquetas}</body></html>`);
  ventana.document.close();
  ventana.focus();
  setTimeout(() => ventana.print(), 300);
}
