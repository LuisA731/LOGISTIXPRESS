"""Fachada del módulo de rutas: planificación, despacho y entrega."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from ..config import ajustes
from ..errores import ErrorNegocio
from ..modelos.dominio import ErrorPlanificacion
from ..seguridad import UsuarioSesion
from .evidencias import ErrorEvidencia, ServicioEvidencias
from .planificador import PlanificadorRutas
from .renderizador import RenderizadorRutas


class ServicioRutas:
    def __init__(
        self,
        *,
        repo,
        renderizador: RenderizadorRutas,
        evidencias: ServicioEvidencias,
        velocidad_kmh: float | None = None,
        minutos_por_entrega: float | None = None,
    ):
        self._repo = repo
        self._render = renderizador
        self._evidencias = evidencias
        self._velocidad = velocidad_kmh or ajustes.velocidad_kmh
        self._minutos = minutos_por_entrega or ajustes.minutos_por_entrega

    def generar_plan(
        self,
        usuario: UsuarioSesion,
        *,
        fecha: date | None = None,
        replanificar: bool = False,
    ) -> dict:
        fecha = fecha or date.today()
        canceladas = 0
        if replanificar:
            canceladas = self._repo.cancelar_planificadas(fecha, usuario)

        pedidos = self._repo.pedidos_listos(bloquear=True)
        if not pedidos:
            return {
                "generado": False,
                "mensaje": (
                    "No hay pedidos en estado LISTO sin ruta activa. "
                    "Registra o libera pedidos para generar un nuevo plan."
                ),
                "fecha": fecha,
                "replanificadas": canceladas,
            }

        vehiculos, conductores = self._repo.flota()
        try:
            planificador = PlanificadorRutas(
                vehiculos,
                conductores,
                velocidad_kmh=self._velocidad,
                minutos_por_entrega=self._minutos,
            )
            plan = planificador.planificar(pedidos, fecha)
        except (ErrorPlanificacion, ValueError) as exc:
            raise ErrorNegocio(str(exc), 409) from exc

        guardadas = self._repo.guardar_plan(plan, usuario)
        viajes = []
        for guardada in guardadas:
            detalle = self._repo.obtener_ruta(guardada["id"])
            if detalle:
                viajes.append(detalle)

        mensaje = (
            f"Plan generado: {len(guardadas)} viaje(s), {plan.total_pedidos} pedido(s) "
            f"y {plan.total_bultos} bulto(s)."
        )
        if canceladas:
            mensaje += f" Se replanificaron {canceladas} ruta(s) previas."
        return {
            "generado": True,
            "mensaje": mensaje,
            "fecha": plan.fecha,
            "total_pedidos": plan.total_pedidos,
            "total_bultos": plan.total_bultos,
            "total_viajes": len(guardadas),
            "distancia_total_km": plan.distancia_total_km,
            "distancia_base_total_km": plan.distancia_base_total_km,
            "ahorro_global_pct": plan.ahorro_global_pct,
            "viajes": viajes,
        }

    def listar(self, *, fecha: date | None = None, estado: str | None = None) -> list[dict]:
        return self._repo.listar_rutas(fecha=fecha, estado=estado)

    def detalle(self, ruta_id: int) -> dict:
        ruta = self._repo.obtener_ruta(ruta_id)
        if ruta is None:
            raise ErrorNegocio("La ruta solicitada no existe.", 404)
        return ruta

    def mapa_png(self, ruta_id: int) -> bytes:
        ruta = self._repo.obtener_ruta(ruta_id)
        if ruta is None:
            raise ErrorNegocio("La ruta solicitada no existe.", 404)
        return self._render.png_de_ruta(ruta)

    def despachar(self, ruta_id: int, guias: list[str], usuario: UsuarioSesion) -> dict:
        if not guias:
            raise ErrorNegocio(
                "Escanea al menos un bulto antes de despachar la unidad.", 400
            )
        resultado = self._repo.despachar(ruta_id, guias, usuario)
        if not resultado["ok"]:
            extra = {}
            if "faltantes" in resultado:
                extra = {
                    "faltantes": resultado.get("faltantes", []),
                    "ajenas": resultado.get("ajenas", []),
                }
            raise ErrorNegocio(resultado["mensaje"], resultado["codigo"], extra)
        return resultado

    def registrar_entrega(self, ruta_id: int, parada_id: int, datos, usuario: UsuarioSesion) -> dict:
        ruta = self._repo.obtener_ruta(ruta_id)
        if ruta is None:
            raise ErrorNegocio("La ruta solicitada no existe.", 404)
        parada = next((p for p in ruta["paradas"] if p["id"] == parada_id), None)
        if parada is None:
            raise ErrorNegocio("La parada no pertenece a la ruta indicada.", 404)
        if ruta["estado"] != "EN_RUTA":
            raise ErrorNegocio(
                f"La ruta {ruta['folio']} debe estar EN_RUTA para registrar entregas.", 409
            )
        if parada["estado"] != "PENDIENTE":
            raise ErrorNegocio("Esta parada ya tiene un resultado registrado.", 409)

        if datos.resultado == "ENTREGADO":
            if not (datos.recibio_nombre or "").strip():
                raise ErrorNegocio(
                    "Registra el nombre de la persona que recibió la mercancía.", 400
                )
            if not datos.firma_base64:
                raise ErrorNegocio(
                    "La firma del cliente es obligatoria para confirmar la entrega.", 400
                )
        else:
            if not datos.motivo_fallo:
                raise ErrorNegocio("Selecciona el motivo de la entrega fallida.", 400)
            if datos.reprogramado_para and datos.reprogramado_para < date.today():
                raise ErrorNegocio(
                    "La fecha de reprogramación no puede estar en el pasado.", 400
                )

        firma_url = None
        foto_url = None
        try:
            firma_url = self._evidencias.guardar(
                ruta_folio=ruta["folio"], parada_id=parada_id,
                tipo="firma", data_url=datos.firma_base64,
            )
            foto_url = self._evidencias.guardar(
                ruta_folio=ruta["folio"], parada_id=parada_id,
                tipo="foto", data_url=datos.foto_base64,
            )
        except ErrorEvidencia as exc:
            self._evidencias.eliminar(firma_url)
            self._evidencias.eliminar(foto_url)
            raise ErrorNegocio(str(exc), 400) from exc

        resultado = self._repo.registrar_entrega(
            ruta_id,
            parada_id,
            resultado=datos.resultado,
            recibio_nombre=(datos.recibio_nombre or "").strip() or None,
            firma_url=firma_url,
            foto_url=foto_url,
            motivo_fallo=datos.motivo_fallo,
            comentario=(datos.comentario or "").strip() or None,
            reprogramado_para=datos.reprogramado_para,
            usuario=usuario,
        )
        if not resultado["ok"]:
            self._evidencias.eliminar(firma_url)
            self._evidencias.eliminar(foto_url)
            raise ErrorNegocio(resultado["mensaje"], resultado["codigo"])

        return {
            "mensaje": resultado["mensaje"],
            "ruta": self.detalle(ruta_id),
        }

    def evidencia(self, entrega_id: int, tipo: str) -> tuple[Path, str]:
        if tipo not in {"firma", "foto"}:
            raise ErrorNegocio("Tipo de evidencia inválido.", 400)
        datos = self._repo.datos_evidencia(entrega_id)
        if datos is None:
            raise ErrorNegocio("La entrega no existe.", 404)
        ruta_relativa = datos["firma_url"] if tipo == "firma" else datos["foto_url"]
        if not ruta_relativa:
            raise ErrorNegocio("Esta entrega no tiene esa evidencia.", 404)
        archivo = self._evidencias.resolver(ruta_relativa)
        if archivo is None:
            raise ErrorNegocio("El archivo de evidencia ya no está disponible.", 404)
        media_type = "image/png" if archivo.suffix.lower() == ".png" else "image/jpeg"
        return archivo, media_type
