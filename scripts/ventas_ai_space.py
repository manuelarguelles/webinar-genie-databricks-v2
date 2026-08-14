#!/usr/bin/env python3
"""Crea el Genie space «Ventas Neptuno AI» — el gemelo CURADO, sobre `neptuno_ai`.

Reconstruye el segundo space del sandbox v5: el A/B del webinar se hace **lado a lado y sin
rollback**, porque cada mitad tiene su propio catálogo y su propio space:

    neptuno.ventas.*      → space «Ventas Neptuno»     (CRUDO, Demo 0)
    neptuno_ai.ventas.*   → space «Ventas Neptuno AI»  (CURADO, este)

Requisito: haber corrido antes `montar_ai.py`, que clona las 8 tablas y les aplica las capas
SQL (1 COMMENT, 5 UC functions, 6 PK/FK). Acá se agregan las capas que viven en el space:
2 (instrucciones), 3 (SQL de confianza) y 4 (vocabulario).

Las instrucciones se leen de `instrucciones-ai.txt` — misma fuente de verdad que en v5.

Uso:
    export GENIE_PROFILE=webinar-aws GENIE_WAREHOUSE=2b2c1ffece1d2787
    python3 ventas_ai_space.py                       # crea
    python3 ventas_ai_space.py --update <space_id>   # re-aplica la curación
"""
import hashlib
import json
import os
import pathlib
import sys

sys.path.insert(0, "/Users/macdenix/clawd/projects/agents-core-ai-databricks")
from lib import genie_client as gc  # noqa: E402

AQUI      = pathlib.Path(__file__).resolve().parent
PROFILE   = os.environ.get("GENIE_PROFILE", "webinar-aws")
WAREHOUSE = os.environ.get("GENIE_WAREHOUSE", "2b2c1ffece1d2787")
CAT       = os.environ.get("GENIE_CATALOG_AI", "neptuno_ai")
ESQ       = os.environ.get("GENIE_SCHEMA", "ventas")

TABLAS = ["categorias", "clientes", "detalles_pedidos", "empleados",
          "pedidos", "productos", "proveedores", "transportistas"]


def lineas(t: str) -> list[str]:
    return t.strip("\n").split("\n")


def uid(clave: str) -> str:
    """UUID de 32 hex sin guiones (lo exige el proto), estable por hash del contenido."""
    return hashlib.md5(clave.encode("utf-8")).hexdigest()


# CAPA 2+4 — misma fuente de verdad que el sandbox v5.
INSTRUCCIONES = (AQUI / "instrucciones-ai.txt").read_text(encoding="utf-8")

# CAPA 3 — SQL de confianza (de genie-space.md), apuntando al catálogo curado.
SQLS = [
    ("Venta neta por categoría y año",
     "Cuánto se vendió (venta neta) por categoría en cada año. Es la forma correcta de "
     "calcular ventas: usa la función venta_neta y FechaPedido.",
     f"""
SELECT c.NombreCategoria,
       YEAR(p.FechaPedido) AS anio,
       ROUND(SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS venta_neta
FROM {CAT}.{ESQ}.detalles_pedidos d
JOIN {CAT}.{ESQ}.pedidos    p  ON p.IdPedido    = d.IdPedido
JOIN {CAT}.{ESQ}.productos  pr ON pr.IdProducto = d.IdProducto
JOIN {CAT}.{ESQ}.categorias c  ON c.IdCategoria = pr.IdCategoria
GROUP BY c.NombreCategoria, YEAR(p.FechaPedido)
ORDER BY anio, venta_neta DESC"""),

    ("Top clientes por venta neta",
     "Ranking de clientes por cuánto compraron (venta neta) en un periodo.",
     f"""
SELECT cl.NombreCompania AS cliente, cl.Pais,
       ROUND(SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS venta_neta,
       COUNT(DISTINCT p.IdPedido) AS pedidos
FROM {CAT}.{ESQ}.detalles_pedidos d
JOIN {CAT}.{ESQ}.pedidos  p  ON p.IdPedido  = d.IdPedido
JOIN {CAT}.{ESQ}.clientes cl ON cl.IdCliente = p.IdCliente
WHERE YEAR(p.FechaPedido) = 2025
GROUP BY cl.NombreCompania, cl.Pais
ORDER BY venta_neta DESC
LIMIT 10"""),

    ("Venta neta por vendedor",
     "Desempeño de la fuerza de ventas: cuánto vendió cada empleado.",
     f"""
SELECT CONCAT(e.Nombre, ' ', e.Apellidos) AS vendedor, e.Cargo,
       ROUND(SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS venta_neta
FROM {CAT}.{ESQ}.detalles_pedidos d
JOIN {CAT}.{ESQ}.pedidos   p ON p.IdPedido   = d.IdPedido
JOIN {CAT}.{ESQ}.empleados e ON e.IdEmpleado = p.IdEmpleado
WHERE YEAR(p.FechaPedido) = 2025
GROUP BY e.Nombre, e.Apellidos, e.Cargo
ORDER BY venta_neta DESC"""),

    ("Evolución mensual de ventas",
     "Serie mensual de venta neta, para ver tendencia.",
     f"""
SELECT DATE_TRUNC('MONTH', p.FechaPedido) AS mes,
       ROUND(SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS venta_neta,
       COUNT(DISTINCT p.IdPedido) AS pedidos
FROM {CAT}.{ESQ}.detalles_pedidos d
JOIN {CAT}.{ESQ}.pedidos p ON p.IdPedido = d.IdPedido
GROUP BY DATE_TRUNC('MONTH', p.FechaPedido)
ORDER BY mes"""),

    ("Impacto del descuento",
     "Cuánto dinero se deja en descuentos: diferencia entre venta bruta y neta.",
     f"""
SELECT YEAR(p.FechaPedido) AS anio,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad), 2) AS venta_bruta,
       ROUND(SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS venta_neta,
       ROUND(SUM(d.PrecioUnidad * d.Cantidad * d.Descuento), 2) AS descuento_otorgado
FROM {CAT}.{ESQ}.detalles_pedidos d
JOIN {CAT}.{ESQ}.pedidos p ON p.IdPedido = d.IdPedido
GROUP BY YEAR(p.FechaPedido)
ORDER BY anio"""),

    ("Pedidos con entrega atrasada",
     "Pedidos enviados después de la fecha comprometida de entrega.",
     f"""
SELECT p.IdPedido, cl.NombreCompania AS cliente,
       p.FechaPedido, p.FechaEntrega, p.FechaEnvio,
       DATEDIFF(p.FechaEnvio, p.FechaEntrega) AS dias_atraso
FROM {CAT}.{ESQ}.pedidos p
JOIN {CAT}.{ESQ}.clientes cl ON cl.IdCliente = p.IdCliente
WHERE p.FechaEnvio > p.FechaEntrega
ORDER BY dias_atraso DESC"""),
]

# Las 6 del A/B del webinar (preguntas-demo.md).
PREGUNTAS = [
    "¿Cuál es el margen de la categoría Bebidas?",
    "¿Cuántos clientes activos tenemos?",
    "Compara las ventas de este año contra el año pasado",
    "¿Cuánto vendimos de la categoría Bebidas el año pasado?",
    "¿Cuál fue el ticket promedio el año pasado?",
    "¿Cuántos productos tenemos a la venta?",
]


def construir() -> dict:
    return {
        "version": 2,
        "data_sources": {
            "tables": [{"identifier": f"{CAT}.{ESQ}.{t}", "column_configs": []} for t in TABLAS]
        },
        "instructions": {
            "text_instructions": [{"id": uid("ti-ventas-ai"), "content": lineas(INSTRUCCIONES)}],
            "example_question_sqls": [
                {"id": uid(f"eq-{titulo}"),
                 "question": lineas(titulo),
                 "sql": lineas(f"-- {desc}\n{sql.strip()}")}
                for titulo, desc, sql in SQLS
            ],
        },
        "config": {
            "sample_questions": [{"id": uid(f"sq-{q}"), "question": lineas(q)} for q in PREGUNTAS]
        },
    }


def main():
    ss = construir()
    w = gc.workspace(PROFILE)
    if "--update" in sys.argv:
        sid = sys.argv[sys.argv.index("--update") + 1]
        res = gc.update_space(w, sid, ss, title="Ventas Neptuno AI")
    else:
        res = gc.create_space(
            w, warehouse_id=WAREHOUSE, serialized_space=ss,
            title="Ventas Neptuno AI",
            description="Gemelo CURADO de Ventas Neptuno — las 6 capas aplicadas (catálogo neptuno_ai)",
        )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
