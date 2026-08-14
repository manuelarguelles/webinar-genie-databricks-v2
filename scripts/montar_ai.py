#!/usr/bin/env python3
"""Monta neptuno_ai: gemelo de neptuno con TODAS las capas SQL aplicadas.

Así el webinar compara A/B en vivo sin rollback:
  neptuno.ventas.*     → crudo   (Demo 0)
  neptuno_ai.ventas.*  → curado  (después de las capas)

Los nombres de tabla son idénticos, así que el mismo SQL corre en ambos.
La fuente de verdad de las capas sigue siendo capas.sql: acá solo se le
reescribe el catálogo."""
import os, re, sys
from dbsql import sql

ORIGEN  = os.environ.get("GENIE_CATALOG", "neptuno")
DESTINO = os.environ.get("GENIE_CATALOG_AI", f"{ORIGEN}_ai")
# MANAGED LOCATION explícito sólo si el metastore lo exige (era el caso del sandbox v5 en
# Azure). En el workspace serverless de AWS el catálogo se crea con el storage por defecto,
# así que se deja vacío y la cláusula ni se emite.
LOC = os.environ.get("GENIE_MANAGED_LOCATION_AI", "")
TABLAS = ["categorias", "transportistas", "proveedores", "clientes",
          "empleados", "productos", "pedidos", "detalles_pedidos"]

def sentencias(ruta):
    """Extrae las sentencias ejecutables de capas.sql (sin comentarios)."""
    crudo = open(ruta, encoding="utf-8").read()
    # fuera el bloque de rollback (todo comentado al final) y los comentarios de línea
    lineas = [l for l in crudo.splitlines() if not l.strip().startswith("--")]
    texto = "\n".join(lineas)
    return [s.strip() for s in texto.split(";") if s.strip()]

print(f"▸ catálogo {DESTINO}")
_loc = f"MANAGED LOCATION '{LOC}' " if LOC else ""
sql(f"CREATE CATALOG IF NOT EXISTS {DESTINO} {_loc}"
    f"COMMENT 'Neptuno CURADO — mismas tablas que neptuno, con las 6 capas aplicadas. "
    f"Gemelo para el A/B del webinar.'")
sql(f"CREATE SCHEMA IF NOT EXISTS {DESTINO}.ventas "
    f"COMMENT 'Modelo estrella de ventas de Neptuno, documentado y gobernado.'")

print("▸ clonando las 8 tablas (DEEP CLONE)")
for t in TABLAS:
    sql(f"CREATE OR REPLACE TABLE {DESTINO}.ventas.{t} "
        f"DEEP CLONE {ORIGEN}.ventas.{t}")
    print(f"   ✓ {t}")

print("\n▸ aplicando las capas SQL (1, 5 y 6) desde capas.sql")
aplicadas, fallidas = 0, []
for st in sentencias("capas.sql"):
    st_ai = re.sub(rf"\b{ORIGEN}\.ventas\.", f"{DESTINO}.ventas.", st)
    st_ai = re.sub(rf"\b{ORIGEN}\.ventas\b", f"{DESTINO}.ventas", st_ai)
    if st_ai.upper().startswith("SELECT"):
        continue  # la query de prueba se corre aparte
    try:
        sql(st_ai, silencioso=True)
        aplicadas += 1
    except Exception as e:
        fallidas.append((st_ai.splitlines()[0][:70], str(e)[:160]))
print(f"   ✓ {aplicadas} sentencias aplicadas")
for cab, err in fallidas:
    print(f"   ✗ {cab} → {err}")

print("\n▸ verificación")
print("  comentarios de tabla:")
sql(f"""SELECT table_name, LEFT(comment, 60) AS comentario
        FROM {DESTINO}.information_schema.tables
        WHERE table_schema='ventas' AND comment IS NOT NULL
        ORDER BY table_name""")
print("\n  columnas trampa documentadas:")
sql(f"""SELECT table_name, column_name, LEFT(comment, 70) AS comentario
        FROM {DESTINO}.information_schema.columns
        WHERE table_schema='ventas' AND comment IS NOT NULL
        ORDER BY table_name, column_name""")
print("\n  función venta_neta (debe dar 103924.31):")
sql(f"""SELECT ROUND(SUM({DESTINO}.ventas.venta_neta(d.PrecioUnidad, d.Cantidad, d.Descuento)), 2) AS prueba
        FROM {DESTINO}.ventas.detalles_pedidos d
        JOIN {DESTINO}.ventas.pedidos    p  ON p.IdPedido    = d.IdPedido
        JOIN {DESTINO}.ventas.productos  pr ON pr.IdProducto = d.IdProducto
        JOIN {DESTINO}.ventas.categorias c  ON c.IdCategoria = pr.IdCategoria
        WHERE c.NombreCategoria='Bebidas' AND YEAR(p.FechaPedido)=2025""")
print("\n  constraints declaradas:")
sql(f"""SELECT COUNT(*) AS constraints FROM {DESTINO}.information_schema.table_constraints
        WHERE table_schema='ventas'""")
print(f"\n✅ {DESTINO}.ventas listo — curado, frente a {ORIGEN}.ventas crudo.")
