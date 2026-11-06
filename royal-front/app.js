'use strict';

/* Arranque del dashboard: sesión persistida, bindings y estado de la API. */

async function actualizarEstadoApi() {
  const indicador = $('#apiStatus');
  if (!indicador) return;
  try {
    const salud = await api('/salud', { permitir401: true });
    indicador.classList.toggle('offline', !salud.base_datos);
    indicador.innerHTML = `<span class="dot"></span>${salud.base_datos ? 'API local' : 'PostgreSQL sin conexión'}`;
  } catch {
    indicador.classList.add('offline');
    indicador.innerHTML = '<span class="dot"></span>API sin conexión';
  }
}

async function arrancar() {
  bindLogin();
  bindShell();
  if (estado.token) {
    try {
      const usuario = await api('/auth/me', { permitir401: true });
      guardarSesion(estado.token, usuario);
      mostrarApp();
    } catch {
      limpiarSesion();
      mostrarLogin();
    }
  } else {
    mostrarLogin();
  }
  actualizarEstadoApi();
  setInterval(() => {
    if (estado.token && !document.hidden) actualizarEstadoApi();
  }, 60000);
  window.addEventListener('resize', () => {
    if (window.innerWidth > 1020) $('#sidebar')?.classList.remove('open');
  });
}

arrancar();
