#!/usr/bin/env python3
"""Crea el Genie space «Radar Comercial Neptuno» — CURADO, sobre `neptuno_ai`.

Tercer caso del research de demanda (28-jul): **Radar comercial** — Casas Bahia bajó de 5-6 h
a 2 min, The AA. Es el seguimiento de la operación comercial: quién vende, quién dejó de
comprar, qué se está cayendo.

Va sobre `neptuno_ai` (catálogo CURADO) como todo space curado: hereda COMMENT, UC functions
y PK/FK. Sólo el space del Demo 0 se queda en `neptuno`.

LAS DOS TRAMPAS QUE CURA (medidas el 14-ago-2026)

1. **El año parcial dispara falsas alarmas.** Los datos terminan el 2026-05-06: 2026 tiene
   5 meses y 2025 tiene 12. Comparándolos de frente, **48 de 79 clientes "caen"**; al
   prorratear, los que caen de verdad son **22**. Son **26 falsas alarmas** — más de la
   mitad del radar sería ruido.

2. **"El mejor vendedor" depende del criterio, y nadie lo dice.** Por venta neta gana
   Margaret Peacock (128.810); por ticket promedio gana Andrew Fuller (1.718), y Margaret
   queda 5ª. Sin declarar el criterio, la respuesta es arbitraria.

Y una tercera, de fondo: **el corte de datos no es hoy.** Hay 100 días de desfase, así que
medir "últimos 12 meses" contra CURRENT_DATE corre la ventana y desaparece actividad real.

Uso:
    export GENIE_PROFILE=webinar-aws GENIE_WAREHOUSE=2b2c1ffece1d2787
    python3 radar_space.py                       # crea
    python3 radar_space.py --update <space_id>   # re-aplica la curación
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, "/Users/macdenix/clawd/projects/agents-core-ai-databricks")
from lib import genie_client as gc  # noqa: E402

PROFILE   = os.environ.get("GENIE_PROFILE", "webinar-aws")
WAREHOUSE = os.environ.get("GENIE_WAREHOUSE", "2b2c1ffece1d2787")
CAT       = os.environ.get("GENIE_CATALOG_AI", "neptuno_ai")
ESQ       = os.environ.get("GENIE_SCHEMA", "ventas")

TABLAS = ["pedidos", "detalles_pedidos", "clientes", "empleados",
          "productos", "categorias", "transportistas"]


def lineas(t: str) -> list[str]:
    return t.strip("\n").split("\n")


def uid(clave: str) -> str:
    """UUID de 32 hex sin guiones (lo exige el proto), estable por hash del contenido."""
    return hashlib.md5(clave.encode("utf-8")).hexdigest()


INSTRUCCIONES = """
Neptuno importa y distribuye alimentos gourmet al por mayor. Este espacio es el RADAR
COMERCIAL: seguimiento de ventas, cartera de clientes y desempeño del equipo comercial.
Responde siempre en español.

EL CORTE DE DATOS NO ES HOY — LÉELO ANTES DE CUALQUIER VENTANA TEMPORAL
- Los datos van de julio 2024 al 6 de mayo de 2026. Ese es el fin del periodo, no la fecha
  actual: hay un desfase de varios meses contra CURRENT_DATE.
- Para ventanas móviles ("últimos 12 meses", "último trimestre") toma como referencia la
  ÚLTIMA FECHA DE PEDIDO de la base, no CURRENT_DATE. Usar la fecha de hoy corre la ventana
  y hace desaparecer actividad que sí existe.

AÑO PARCIAL — LA CAUSA Nº1 DE FALSAS ALARMAS
- 2025 es el último año COMPLETO. 2026 sólo llega hasta mayo: son 5 meses contra 12.
- NUNCA compares 2026 contra 2025 de frente sin advertirlo. Comparados así, 48 de 79
  clientes "caen"; prorrateando, los que caen de verdad son 22. El resto es ruido.
- Al comparar un año parcial contra uno completo: (a) avisa siempre, y (b) ofrece la
  comparación correcta — mismo rango de meses en ambos años, o prorrateo.

"EL MEJOR" EXIGE UN CRITERIO
- Cuando pidan "el mejor vendedor", "el mejor cliente" o "el que más creció", di con qué
  criterio estás respondiendo, porque el ranking cambia:
  por venta neta gana uno, por ticket promedio otro, por número de clientes otro.
- Si la pregunta no lo aclara, responde por VENTA NETA y menciona explícitamente que ése
  es el criterio, ofreciendo los otros.

DEFINICIONES
- Venta neta: usa la función venta_neta(precio, cantidad, descuento). El Cargo del pedido
  es flete, es un COSTO y NUNCA se suma a las ventas.
- Cliente activo: con al menos un pedido en los últimos 12 meses respecto del corte de datos.
- Cliente en riesgo / dormido: sin pedidos en los últimos 6 meses respecto del corte, pero
  con historial previo.
- Cliente perdido / churn: sin pedidos en los últimos 12 meses respecto del corte.
- Ticket promedio: venta neta dividida entre número de pedidos DISTINTOS.
- Concentración de cartera: qué porcentaje de la venta aportan los N clientes más grandes.
- NO hay costo de mercadería: no calcules margen, utilidad ni rentabilidad por cliente o
  vendedor. Si lo piden, acláralo y ofrece la venta neta.

VOCABULARIO
- venta / facturación / ingresos / revenue -> venta neta
- vendedor / comercial / asesor / representante / ejecutivo -> empleados (Nombre + Apellidos)
- cartera / cuentas / clientes -> clientes.NombreCompania
- se cayó / bajó / perdió / dejó de comprar -> variación negativa o inactividad
- dormido / en riesgo / frío -> sin pedidos en los últimos 6 meses del corte
- churn / fuga / perdido -> sin pedidos en los últimos 12 meses del corte
- cumplimiento / entrega a tiempo -> FechaEnvio vs FechaEntrega

VALORES REALES
- 9 vendedores, 89 clientes con pedidos, 3 transportistas, 830 pedidos.
- Transportistas: Expreso Veloz, Paquetes Unidos, Envios Federales.
- Categorías: Bebidas, Condimentos, Reposteria, Lacteos, Granos y Cereales, Carnes y Aves,
  Frutas y Verduras, Pescados y Mariscos.
"""

SQLS = [
    ("Clientes que caen — comparación justa",
     "Variación por cliente comparando el MISMO rango de meses (enero a mayo) en 2025 y 2026. "
     "Ésta es la forma correcta de detectar caídas: comparar 2026 completo contra 2025 completo "
     "marca 48 clientes en caída cuando en realidad son 22.",
     f"""
WITH ventana AS (
  SELECT p.IdCliente, YEAR(p.FechaPedido) AS anio,
         SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)) AS neto
  FROM {CAT}.{ESQ}.detalles_pedidos d
  JOIN {CAT}.{ESQ}.pedidos p ON p.IdPedido = d.IdPedido
  WHERE YEAR(p.FechaPedido) IN (2025, 2026) AND MONTH(p.FechaPedido) <= 5
  GROUP BY p.IdCliente, YEAR(p.FechaPedido)
)
SELECT cl.NombreCompania AS cliente, cl.Pais,
       ROUND(a25.neto, 2) AS ene_may_2025,
       ROUND(a26.neto, 2) AS ene_may_2026,
       ROUND(a26.neto - a25.neto, 2) AS variacion,
       ROUND(try_divide(a26.neto - a25.neto, a25.neto) * 100, 1) AS variacion_pct
FROM (SELECT * FROM ventana WHERE anio = 2025) a25
JOIN (SELECT * FROM ventana WHERE anio = 2026) a26 ON a25.IdCliente = a26.IdCliente
JOIN {CAT}.{ESQ}.clientes cl ON cl.IdCliente = a25.IdCliente
ORDER BY variacion ASC"""),

    ("Clientes en riesgo y perdidos",
     "Clientes clasificados por cuánto hace que no compran, medido contra el CORTE DE DATOS "
     "(último pedido de la base), no contra la fecha de hoy.",
     f"""
WITH corte AS (SELECT MAX(FechaPedido) AS fin FROM {CAT}.{ESQ}.pedidos),
ultimo AS (
  SELECT p.IdCliente, MAX(p.FechaPedido) AS ultima_compra,
         COUNT(DISTINCT p.IdPedido) AS pedidos_historicos
  FROM {CAT}.{ESQ}.pedidos p GROUP BY p.IdCliente
)
SELECT cl.NombreCompania AS cliente, cl.Pais,
       u.ultima_compra, u.pedidos_historicos,
       DATEDIFF((SELECT fin FROM corte), u.ultima_compra) AS dias_sin_comprar,
       CASE
         WHEN u.ultima_compra < ADD_MONTHS((SELECT fin FROM corte), -12) THEN 'perdido'
         WHEN u.ultima_compra < ADD_MONTHS((SELECT fin FROM corte),  -6) THEN 'en riesgo'
         ELSE 'activo'
       END AS estado
FROM ultimo u
JOIN {CAT}.{ESQ}.clientes cl ON cl.IdCliente = u.IdCliente
ORDER BY dias_sin_comprar DESC"""),

    ("Ranking de vendedores por los tres criterios",
     "Desempeño comercial con los tres criterios a la vez, porque 'el mejor' cambia según cuál "
     "se use: por venta neta gana Margaret Peacock, por ticket promedio gana Andrew Fuller.",
     f"""
SELECT CONCAT(e.Nombre, ' ', e.Apellidos) AS vendedor, e.Cargo,
       ROUND(SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS venta_neta,
       COUNT(DISTINCT p.IdPedido)  AS pedidos,
       COUNT(DISTINCT p.IdCliente) AS clientes_atendidos,
       ROUND(try_divide(SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)),
                        COUNT(DISTINCT p.IdPedido)), 2) AS ticket_promedio
FROM {CAT}.{ESQ}.detalles_pedidos d
JOIN {CAT}.{ESQ}.pedidos   p ON p.IdPedido   = d.IdPedido
JOIN {CAT}.{ESQ}.empleados e ON e.IdEmpleado = p.IdEmpleado
WHERE YEAR(p.FechaPedido) = 2025
GROUP BY e.Nombre, e.Apellidos, e.Cargo
ORDER BY venta_neta DESC"""),

    ("Concentración de cartera",
     "Cuánto pesa cada cliente sobre la venta total y su acumulado: sirve para ver si el "
     "negocio depende de pocas cuentas.",
     f"""
WITH v AS (
  SELECT p.IdCliente,
         SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)) AS neto
  FROM {CAT}.{ESQ}.detalles_pedidos d
  JOIN {CAT}.{ESQ}.pedidos p ON p.IdPedido = d.IdPedido
  WHERE YEAR(p.FechaPedido) = 2025
  GROUP BY p.IdCliente
)
SELECT cl.NombreCompania AS cliente,
       ROUND(v.neto, 2) AS venta_neta,
       ROUND(v.neto * 100.0 / SUM(v.neto) OVER (), 2) AS pct_del_total,
       ROUND(SUM(v.neto) OVER (ORDER BY v.neto DESC) * 100.0 / SUM(v.neto) OVER (), 2) AS pct_acumulado
FROM v JOIN {CAT}.{ESQ}.clientes cl ON cl.IdCliente = v.IdCliente
ORDER BY venta_neta DESC"""),

    ("Cumplimiento de entrega por transportista",
     "Pedidos enviados después de la fecha comprometida, agrupados por transportista.",
     f"""
SELECT t.NombreCompania AS transportista,
       COUNT(*) AS pedidos_enviados,
       SUM(CASE WHEN p.FechaEnvio > p.FechaEntrega THEN 1 ELSE 0 END) AS atrasados,
       ROUND(SUM(CASE WHEN p.FechaEnvio > p.FechaEntrega THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_atraso
FROM {CAT}.{ESQ}.pedidos p
JOIN {CAT}.{ESQ}.transportistas t ON t.IdTransportista = p.IdTransportista
WHERE p.FechaEnvio IS NOT NULL
GROUP BY t.NombreCompania
ORDER BY pct_atraso DESC"""),

    ("Evolución mensual con año completo vs parcial",
     "Serie mensual de venta neta marcando qué meses pertenecen al año parcial 2026, para no "
     "leer la caída del final como una tendencia real.",
     f"""
SELECT DATE_TRUNC('MONTH', p.FechaPedido) AS mes,
       ROUND(SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS venta_neta,
       COUNT(DISTINCT p.IdPedido) AS pedidos,
       CASE WHEN YEAR(p.FechaPedido) = 2026 THEN 'año parcial' ELSE 'año completo' END AS periodo
FROM {CAT}.{ESQ}.detalles_pedidos d
JOIN {CAT}.{ESQ}.pedidos p ON p.IdPedido = d.IdPedido
GROUP BY DATE_TRUNC('MONTH', p.FechaPedido), YEAR(p.FechaPedido)
ORDER BY mes"""),

    ("Categorías que se están cayendo",
     "Variación por categoría comparando el mismo rango de meses (enero a mayo) de 2025 y 2026.",
     f"""
WITH v AS (
  SELECT c.NombreCategoria, YEAR(p.FechaPedido) AS anio,
         SUM({CAT}.{ESQ}.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)) AS neto
  FROM {CAT}.{ESQ}.detalles_pedidos d
  JOIN {CAT}.{ESQ}.pedidos    p  ON p.IdPedido    = d.IdPedido
  JOIN {CAT}.{ESQ}.productos  pr ON pr.IdProducto = d.IdProducto
  JOIN {CAT}.{ESQ}.categorias c  ON c.IdCategoria = pr.IdCategoria
  WHERE YEAR(p.FechaPedido) IN (2025, 2026) AND MONTH(p.FechaPedido) <= 5
  GROUP BY c.NombreCategoria, YEAR(p.FechaPedido)
)
SELECT a25.NombreCategoria AS categoria,
       ROUND(a25.neto, 2) AS ene_may_2025,
       ROUND(a26.neto, 2) AS ene_may_2026,
       ROUND(try_divide(a26.neto - a25.neto, a25.neto) * 100, 1) AS variacion_pct
FROM (SELECT * FROM v WHERE anio = 2025) a25
JOIN (SELECT * FROM v WHERE anio = 2026) a26 ON a25.NombreCategoria = a26.NombreCategoria
ORDER BY variacion_pct ASC"""),
]

PREGUNTAS = [
    "¿Qué clientes se están cayendo?",
    "¿Qué clientes dejaron de comprar?",
    "¿Quién es mi mejor vendedor?",
    "¿Cuánto depende el negocio de mis 10 mejores clientes?",
    "¿Qué categorías están cayendo este año?",
    "¿Qué transportista se atrasa más?",
]


def construir() -> dict:
    return {
        "version": 2,
        "data_sources": {
            "tables": [{"identifier": f"{CAT}.{ESQ}.{t}", "column_configs": []} for t in TABLAS]
        },
        "instructions": {
            "text_instructions": [{"id": uid("ti-radar"), "content": lineas(INSTRUCCIONES)}],
            "example_question_sqls": [
                {"id": uid(f"eq-radar-{titulo}"),
                 "question": lineas(titulo),
                 "sql": lineas(f"-- {desc}\n{sql.strip()}")}
                for titulo, desc, sql in SQLS
            ],
        },
        "config": {
            "sample_questions": [{"id": uid(f"sq-radar-{q}"), "question": lineas(q)}
                                 for q in PREGUNTAS]
        },
    }


def main():
    ss = construir()
    w = gc.workspace(PROFILE)
    if "--update" in sys.argv:
        sid = sys.argv[sys.argv.index("--update") + 1]
        res = gc.update_space(w, sid, ss, title="Radar Comercial Neptuno")
    else:
        res = gc.create_space(
            w, warehouse_id=WAREHOUSE, serialized_space=ss,
            title="Radar Comercial Neptuno",
            description="Cartera, caídas y desempeño del equipo comercial — space CURADO",
        )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
