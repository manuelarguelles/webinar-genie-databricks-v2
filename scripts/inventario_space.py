#!/usr/bin/env python3
"""Crea el Genie space «Inventario Neptuno» — CURADO desde el minuto cero.

A diferencia de «Ventas Neptuno» (que nace crudo a propósito, porque el Demo 0 del webinar
necesita verlo fallar), este space se entrega ya curado: instrucciones de negocio, SQL de
confianza y preguntas de ejemplo.

🔑 VA SOBRE `neptuno_ai`, EL CATÁLOGO CURADO
Un space curado se apoya en el catálogo curado: así hereda la capa 1 (COMMENT), la 5 (UC
functions) y la 6 (PK/FK) que `montar_ai.py` ya aplicó, y sólo agrega las capas que viven en
el space (2 instrucciones, 3 SQL de confianza, 4 vocabulario).

⚠️ Los COMMENT son **globales al metastore**, así que ponerlos en `neptuno` (crudo) arruinaría
el Demo 0 del space «Ventas Neptuno», que comparte esas tablas. En `neptuno_ai` no hay ese
riesgo: es un catálogo aparte, clonado justamente para estar curado. La capa 1 propia de
inventario (UnidadesEnPedido, NivelNuevoPedido) está en `capas-inventario.sql`.

El caso de negocio (research de demanda del 28-jul): **Inventario** es uno de los 11 tipos de
Genie con cliente y cifra pública — HP (miles de SKU), Casas Bahia, Conagra.

Uso:
    export GENIE_PROFILE=webinar-aws GENIE_WAREHOUSE=2b2c1ffece1d2787
    python3 inventario_space.py            # crea (sobre neptuno_ai)
    python3 inventario_space.py --update <space_id>   # re-aplica la curación
"""
import json
import os
import sys

sys.path.insert(0, "/Users/macdenix/clawd/projects/agents-core-ai-databricks")
from lib import genie_client as gc  # noqa: E402

PROFILE   = os.environ.get("GENIE_PROFILE", "webinar-aws")
WAREHOUSE = os.environ.get("GENIE_WAREHOUSE", "2b2c1ffece1d2787")
CAT       = os.environ.get("GENIE_CATALOG_AI", "neptuno_ai")
ESQ       = os.environ.get("GENIE_SCHEMA", "ventas")

TABLAS = ["productos", "categorias", "proveedores", "detalles_pedidos", "pedidos"]


def lineas(texto: str) -> list[str]:
    """El proto de Genie espera los textos largos como lista de líneas."""
    return texto.strip("\n").split("\n")


def uid(clave: str) -> str:
    """Los ids del proto deben ser UUID de 32 hex en minúscula y SIN guiones
    (la API rechaza 'sq-01' con 'Expected lowercase 32-hex UUID without hyphens').
    Se derivan por hash del contenido para que sean estables entre corridas:
    así un --update no reescribe los ids ni duplica entradas.
    """
    import hashlib
    return hashlib.md5(clave.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────
# CAPA 2+4 · Instrucciones de negocio (lo que el esquema no dice)
# ─────────────────────────────────────────────────────────────────────────
INSTRUCCIONES = f"""
Neptuno importa y distribuye alimentos gourmet al por mayor. Este espacio responde
preguntas de INVENTARIO y REPOSICIÓN. Responde siempre en español.

LA REGLA QUE MÁS SE EQUIVOCA — QUÉ HAY QUE REPONER
- Un producto necesita reposición cuando el stock disponible YA NO ALCANZA el punto de
  reorden, contando lo que viene en camino:
      (UnidadesEnExistencia + UnidadesEnPedido) <= NivelNuevoPedido
- UnidadesEnPedido es mercadería YA PEDIDA al proveedor que todavía no llegó. Un producto
  con 0 en existencia pero 70 en pedido NO hay que volver a comprarlo: ya está resuelto.
  Ignorar UnidadesEnPedido genera órdenes de compra duplicadas.
- Nunca incluyas productos con Suspendido = 1: están descontinuados, no se reponen.

DEFINICIONES
- Stock disponible = UnidadesEnExistencia (lo que hay físicamente hoy en almacén).
- En tránsito / en camino / por llegar = UnidadesEnPedido.
- Punto de reorden = NivelNuevoPedido. Si es 0, el producto no se repone automáticamente.
- Producto vigente = Suspendido = 0. Producto descontinuado = Suspendido = 1.
- Stock muerto = unidades en existencia de productos descontinuados. No es inventario
  vendible: al reportar "nivel de inventario" cuenta sólo los vigentes y, si el total
  incluye descontinuados, acláralo.
- Quiebre de stock = UnidadesEnExistencia = 0 en un producto vigente.

VALORACIÓN — LÍMITE IMPORTANTE
- El modelo NO tiene costo de mercadería. Se puede valorizar el inventario a PRECIO DE
  LISTA (productos.PrecioUnidad), pero eso NO es el costo ni el valor contable.
  Si piden "valor del inventario", entrega la valorización a precio de lista y aclara
  explícitamente que no hay costos. NUNCA calcules margen ni utilidad.

CONSUMO Y COBERTURA
- La demanda histórica sale de detalles_pedidos (Cantidad), unida a pedidos por IdPedido
  y fechada por pedidos.FechaPedido.
- Los datos van de julio 2024 a mayo 2026. "El año pasado" = 2025 (último año completo).
- Cobertura en días = stock disponible / consumo diario promedio del periodo pedido.

VOCABULARIO
- reponer / reabastecer / comprar / ordenar / restock -> productos bajo punto de reorden
- stock / existencias / inventario / disponible -> UnidadesEnExistencia
- en camino / en tránsito / pendiente de llegar / ya pedido -> UnidadesEnPedido
- quiebre / rotura de stock / agotado / sin stock -> UnidadesEnExistencia = 0
- descontinuado / dado de baja / suspendido -> Suspendido = 1
- rubro / línea / familia -> categorias.NombreCategoria
- SKU / artículo / ítem -> productos.NombreProducto

VALORES REALES (para que los filtros no fallen)
- Categorías: Bebidas, Condimentos, Reposteria, Lacteos, Granos y Cereales,
  Carnes y Aves, Frutas y Verduras, Pescados y Mariscos.
- Hay 77 productos: 67 vigentes y 10 descontinuados.
"""

# ─────────────────────────────────────────────────────────────────────────
# CAPA 3 · SQL de confianza — el que más mueve la aguja
# ─────────────────────────────────────────────────────────────────────────
SQLS = [
    (
        "Productos que hay que reponer",
        "Productos vigentes cuyo stock disponible MÁS lo que ya viene en camino no alcanza "
        "el punto de reorden. Ésta es la forma correcta de responder qué reponer: descuenta "
        "UnidadesEnPedido para no duplicar órdenes de compra.",
        f"""
SELECT p.NombreProducto,
       c.NombreCategoria,
       p.UnidadesEnExistencia AS stock,
       p.UnidadesEnPedido     AS en_camino,
       p.NivelNuevoPedido     AS punto_reorden,
       (p.NivelNuevoPedido - p.UnidadesEnExistencia - p.UnidadesEnPedido) AS faltante
FROM {CAT}.{ESQ}.productos p
JOIN {CAT}.{ESQ}.categorias c ON c.IdCategoria = p.IdCategoria
WHERE p.Suspendido = 0
  AND p.NivelNuevoPedido > 0
  AND (p.UnidadesEnExistencia + p.UnidadesEnPedido) <= p.NivelNuevoPedido
ORDER BY faltante DESC
""",
    ),
    (
        "Falsos positivos de reposición",
        "Productos que PARECEN necesitar reposición si sólo se mira el stock, pero que ya "
        "tienen mercadería en camino. Sirve para explicar por qué el conteo ingenuo infla.",
        f"""
SELECT p.NombreProducto,
       p.UnidadesEnExistencia AS stock,
       p.UnidadesEnPedido     AS en_camino,
       p.NivelNuevoPedido     AS punto_reorden
FROM {CAT}.{ESQ}.productos p
WHERE p.Suspendido = 0
  AND p.UnidadesEnExistencia <= p.NivelNuevoPedido
  AND p.UnidadesEnPedido > 0
ORDER BY p.UnidadesEnPedido DESC
""",
    ),
    (
        "Nivel de inventario vigente vs stock muerto",
        "Unidades en existencia separando productos vigentes de descontinuados. El nivel de "
        "inventario que se reporta al negocio es el de los vigentes.",
        f"""
SELECT SUM(CASE WHEN Suspendido = 0 THEN UnidadesEnExistencia ELSE 0 END) AS inventario_vigente,
       SUM(CASE WHEN Suspendido = 1 THEN UnidadesEnExistencia ELSE 0 END) AS stock_muerto,
       SUM(UnidadesEnExistencia)                                          AS total_bruto
FROM {CAT}.{ESQ}.productos
""",
    ),
    (
        "Quiebres de stock",
        "Productos vigentes agotados (cero existencias), indicando si tienen reposición en curso.",
        f"""
SELECT p.NombreProducto,
       c.NombreCategoria,
       p.UnidadesEnPedido AS en_camino,
       CASE WHEN p.UnidadesEnPedido > 0 THEN 'reposición en curso'
            ELSE 'sin reposición' END AS situacion
FROM {CAT}.{ESQ}.productos p
JOIN {CAT}.{ESQ}.categorias c ON c.IdCategoria = p.IdCategoria
WHERE p.Suspendido = 0 AND p.UnidadesEnExistencia = 0
ORDER BY p.UnidadesEnPedido DESC
""",
    ),
    (
        "Inventario valorizado a precio de lista por categoría",
        "Valorización del stock vigente usando el precio de LISTA. Ojo: no es costo ni valor "
        "contable, porque el modelo no tiene costo de mercadería.",
        f"""
SELECT c.NombreCategoria,
       COUNT(*)                                            AS skus_vigentes,
       SUM(p.UnidadesEnExistencia)                         AS unidades,
       ROUND(SUM(p.UnidadesEnExistencia * p.PrecioUnidad), 2) AS valor_a_precio_lista
FROM {CAT}.{ESQ}.productos p
JOIN {CAT}.{ESQ}.categorias c ON c.IdCategoria = p.IdCategoria
WHERE p.Suspendido = 0
GROUP BY c.NombreCategoria
ORDER BY valor_a_precio_lista DESC
""",
    ),
    (
        "Cobertura de inventario en días",
        "Cuántos días de venta aguanta el stock actual, según el consumo promedio de 2025. "
        "Une el inventario con la demanda real de detalles_pedidos.",
        f"""
WITH consumo AS (
  SELECT d.IdProducto,
         SUM(d.Cantidad) / 365.0 AS unidades_por_dia
  FROM {CAT}.{ESQ}.detalles_pedidos d
  JOIN {CAT}.{ESQ}.pedidos p ON p.IdPedido = d.IdPedido
  WHERE YEAR(p.FechaPedido) = 2025
  GROUP BY d.IdProducto
)
SELECT pr.NombreProducto,
       pr.UnidadesEnExistencia AS stock,
       ROUND(c.unidades_por_dia, 3) AS consumo_diario,
       ROUND(try_divide(pr.UnidadesEnExistencia, c.unidades_por_dia), 1) AS dias_de_cobertura
FROM {CAT}.{ESQ}.productos pr
JOIN consumo c ON c.IdProducto = pr.IdProducto
WHERE pr.Suspendido = 0
ORDER BY dias_de_cobertura ASC
""",
    ),
    (
        "Productos descontinuados que aún tienen stock",
        "Productos dados de baja que siguen ocupando almacén. Candidatos a liquidación.",
        f"""
SELECT p.NombreProducto,
       c.NombreCategoria,
       p.UnidadesEnExistencia AS stock,
       ROUND(p.UnidadesEnExistencia * p.PrecioUnidad, 2) AS valor_a_precio_lista
FROM {CAT}.{ESQ}.productos p
JOIN {CAT}.{ESQ}.categorias c ON c.IdCategoria = p.IdCategoria
WHERE p.Suspendido = 1 AND p.UnidadesEnExistencia > 0
ORDER BY valor_a_precio_lista DESC
""",
    ),
]

PREGUNTAS_SUGERIDAS = [
    "¿Qué productos tengo que reponer?",
    "¿Cuál es mi nivel de inventario?",
    # Antes era «…y no tienen reposición en curso?»: correcta pero devolvía vacío
    # (los 5 quiebres ya tienen mercadería en camino), y como tarjeta de portada no sirve.
    "¿Qué productos están agotados?",
    "¿Cuántos días de cobertura tengo por producto?",
    "¿Cuánto vale mi inventario por categoría?",
    "¿Qué productos descontinuados siguen ocupando almacén?",
]


def construir() -> dict:
    return {
        "version": 2,
        "data_sources": {
            "tables": [{"identifier": f"{CAT}.{ESQ}.{t}", "column_configs": []} for t in TABLAS]
        },
        "instructions": {
            "text_instructions": [{"id": uid("ti-inventario"), "content": lineas(INSTRUCCIONES)}],
            # `example_question_sqls` sólo acepta question + sql: NO tiene campo de
            # descripción (la API rechaza `content` con "Unknown field"). La descripción
            # se conserva como comentario al tope del SQL, que Genie igual lee.
            "example_question_sqls": [
                {"id": uid(f"eq-{titulo}"),
                 "question": lineas(titulo),
                 "sql": lineas(f"-- {desc}\n{sql.strip()}")}
                for i, (titulo, desc, sql) in enumerate(SQLS, start=1)
            ],
        },
        "config": {
            "sample_questions": [{"id": uid(f"sq-{q}"), "question": lineas(q)}
                                 for q in PREGUNTAS_SUGERIDAS]
        },
    }


def main():
    ss = construir()
    w = gc.workspace(PROFILE)
    if "--update" in sys.argv:
        space_id = sys.argv[sys.argv.index("--update") + 1]
        res = gc.update_space(w, space_id, ss, title="Inventario Neptuno")
    else:
        res = gc.create_space(
            w, warehouse_id=WAREHOUSE, serialized_space=ss,
            title="Inventario Neptuno",
            description="Reposición, quiebres y cobertura de stock — space CURADO",
        )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
