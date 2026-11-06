from pathlib import Path

import pytest

from app.servicios.evidencias import ErrorEvidencia, ServicioEvidencias

PNG_1X1 = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_guardar_y_resolver_evidencia(tmp_path: Path):
    servicio = ServicioEvidencias(tmp_path, max_mb=1)
    ruta = servicio.guardar(
        ruta_folio="R-20261105-1000", parada_id=4, tipo="firma", data_url=PNG_1X1
    )
    assert ruta is not None
    archivo = servicio.resolver(ruta)
    assert archivo is not None and archivo.is_file()
    assert archivo.read_bytes().startswith(b"\x89PNG")
    servicio.eliminar(ruta)
    assert servicio.resolver(ruta) is None


def test_rechaza_formatos_no_soportados(tmp_path: Path):
    servicio = ServicioEvidencias(tmp_path)
    with pytest.raises(ErrorEvidencia):
        servicio.guardar(
            ruta_folio="R-1", parada_id=1, tipo="foto",
            data_url="data:text/plain;base64,aG9sYQ==",
        )
    with pytest.raises(ErrorEvidencia):
        servicio.guardar(
            ruta_folio="R-1", parada_id=1, tipo="foto",
            data_url="data:image/png;base64,AAAA",
        )


def test_no_permite_escapar_del_directorio(tmp_path: Path):
    servicio = ServicioEvidencias(tmp_path)
    assert servicio.resolver("../../etc/passwd") is None
