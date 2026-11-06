from app.servicios.renderizador import RenderizadorRutas


def test_renderiza_png_con_ruta():
    ruta = {
        "folio": "R-20261105-1000",
        "zona": "NORTE",
        "conductor": {"nombre": "R. Aguilar", "placas": "LX-4821"},
        "vehiculo": {"placas": "LX-4821"},
        "num_paradas": 2,
        "num_bultos": 4,
        "peso_total_kg": 120.5,
        "volumen_total_m3": 0.8,
        "distancia_km": 24.3,
        "distancia_base_km": 30.1,
        "ahorro_pct": 19.3,
        "eta_min": 62,
        "paradas": [
            {
                "secuencia": 1, "cliente": "Cliente A",
                "latitud": 25.72, "longitud": -100.30,
            },
            {
                "secuencia": 2, "cliente": "Cliente B",
                "latitud": 25.77, "longitud": -100.27,
            },
        ],
    }
    png = RenderizadorRutas().png_de_ruta(ruta)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 10000
