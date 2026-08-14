#!/usr/bin/env python3
"""Reconstruye Neptuno completo en un workspace Databricks NUEVO, de cero a Genie-listo.

Cubre los dos pasos que en julio se hicieron a mano y no quedaron scriptados:
el catálogo/schema/volumen y la subida de los CSVs. Después crea las 8 tablas
DESNUDAS (sin COMMENT ni PK/FK: el Demo 0 necesita el Genie crudo) y verifica
por efecto contra las cifras validadas del webinar del 23-jul.

Uso:
    export GENIE_PROFILE=<perfil de ~/.databrickscfg>
    export GENIE_WAREHOUSE=<warehouse_id serverless>
    export GENIE_CATALOG=neptuno       # opcional
    export GENIE_SCHEMA=ventas         # opcional
    export GENIE_MANAGED_LOCATION=...  # opcional, ver gotcha abajo
    python3 bootstrap.py

Gotcha heredado del build de julio: si el metastore usa Default Storage,
`CREATE CATALOG` falla salvo con MANAGED LOCATION explícito. Si eso pasa y no
diste GENIE_MANAGED_LOCATION, el script cae de vuelta a crear sólo un schema
dentro de un catálogo que ya exista (GENIE_FALLBACK_CATALOG, default `main`).
"""
import json
import os
import pathlib
import subprocess
import sys

from dbsql import PROFILE, WAREHOUSE, sql
from crear_tablas import CAT, ESQ, ESQUEMAS, VOL, crear_todas

AQUI = pathlib.Path(__file__).resolve().parent
CSV_DIR = AQUI / "csv"
MANAGED_LOCATION = os.environ.get("GENIE_MANAGED_LOCATION")
FALLBACK_CATALOG = os.environ.get("GENIE_FALLBACK_CATALOG", "main")

# Cifras validadas contra Databricks el 23-jul-2026 (ver README).
ESPERADO_FILAS = {"pedidos": 830, "detalles_pedidos": 2155}
ESPERADO_BEBIDAS_2025 = 103924.31
ESPERADO_NETO_2025 = 617085.20


def cli(*args):
    p = subprocess.run(["databricks", *args, "-p", PROFILE],
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def paso(titulo):
    print(f"\n=== {titulo} ===")


def crear_contenedores():
    """Catálogo + schema + volumen. Devuelve (catalogo, schema) realmente usados."""
    global CAT
    paso(f"catálogo `{CAT}`")
    try:
        if MANAGED_LOCATION:
            sql(f"CREATE CATALOG IF NOT EXISTS {CAT} MANAGED LOCATION '{MANAGED_LOCATION}'")
        else:
            sql(f"CREATE CATALOG IF NOT EXISTS {CAT}")
        print(f"  ✅ {CAT}")
    except Exception as e:
        print(f"  ⚠️  no se pudo crear el catálogo: {str(e)[:200]}")
        print(f"  ↪ fallback: uso el catálogo existente `{FALLBACK_CATALOG}`")
        CAT = FALLBACK_CATALOG

    paso(f"schema `{CAT}.{ESQ}`")
    sql(f"CREATE SCHEMA IF NOT EXISTS {CAT}.{ESQ}")
    print(f"  ✅ {CAT}.{ESQ}")

    paso(f"volumen `{CAT}.{ESQ}.landing`")
    sql(f"CREATE VOLUME IF NOT EXISTS {CAT}.{ESQ}.landing")
    print(f"  ✅ /Volumes/{CAT}/{ESQ}/landing")
    return CAT, ESQ


def subir_csvs(catalogo, esquema):
    paso("subida de los 8 CSVs")
    destino_base = f"dbfs:/Volumes/{catalogo}/{esquema}/landing"
    faltantes = [t for t in ESQUEMAS if not (CSV_DIR / f"{t}.csv").exists()]
    if faltantes:
        sys.exit(f"❌ faltan CSVs en {CSV_DIR}: {', '.join(faltantes)}")

    for tabla in ESQUEMAS:
        origen = CSV_DIR / f"{tabla}.csv"
        rc, _, err = cli("fs", "cp", "--overwrite", str(origen), f"{destino_base}/{tabla}.csv")
        if rc != 0:
            sys.exit(f"❌ falló la subida de {tabla}.csv: {err[:300]}")
        print(f"  ✅ {tabla}.csv ({origen.stat().st_size:,} bytes)")


def verificar(catalogo, esquema):
    """Verificación por efecto: las cifras tienen que coincidir con las del webinar."""
    paso("verificación contra las cifras validadas del 23-jul")
    ok = True

    for tabla, esperado in ESPERADO_FILAS.items():
        filas = int(sql(f"SELECT COUNT(*) FROM {catalogo}.{esquema}.{tabla}",
                        silencioso=True)[0][0])
        marca = "✅" if filas == esperado else "❌"
        if filas != esperado:
            ok = False
        print(f"  {marca} {tabla}: {filas:,} filas (esperado {esperado:,})")

    bebidas = float(sql(f"""
        SELECT ROUND(SUM(dp.PrecioUnidad * dp.Cantidad * (1 - dp.Descuento)), 2)
        FROM {catalogo}.{esquema}.detalles_pedidos dp
        JOIN {catalogo}.{esquema}.pedidos p    ON p.IdPedido = dp.IdPedido
        JOIN {catalogo}.{esquema}.productos pr ON pr.IdProducto = dp.IdProducto
        JOIN {catalogo}.{esquema}.categorias c ON c.IdCategoria = pr.IdCategoria
        WHERE c.NombreCategoria = 'Bebidas' AND YEAR(p.FechaPedido) = 2025
    """, silencioso=True)[0][0])
    marca = "✅" if abs(bebidas - ESPERADO_BEBIDAS_2025) < 0.02 else "❌"
    if marca == "❌":
        ok = False
    print(f"  {marca} ancla · Bebidas 2025 neto: {bebidas:,.2f} "
          f"(esperado {ESPERADO_BEBIDAS_2025:,.2f})")

    neto = float(sql(f"""
        SELECT ROUND(SUM(dp.PrecioUnidad * dp.Cantidad * (1 - dp.Descuento)), 2)
        FROM {catalogo}.{esquema}.detalles_pedidos dp
        JOIN {catalogo}.{esquema}.pedidos p ON p.IdPedido = dp.IdPedido
        WHERE YEAR(p.FechaPedido) = 2025
    """, silencioso=True)[0][0])
    marca = "✅" if abs(neto - ESPERADO_NETO_2025) < 0.02 else "❌"
    if marca == "❌":
        ok = False
    print(f"  {marca} venta neta total 2025: {neto:,.2f} "
          f"(esperado {ESPERADO_NETO_2025:,.2f})")

    return ok


def main():
    print(f"perfil={PROFILE}  warehouse={WAREHOUSE}  destino={CAT}.{ESQ}")
    if not os.environ.get("GENIE_PROFILE") or not os.environ.get("GENIE_WAREHOUSE"):
        print("⚠️  GENIE_PROFILE / GENIE_WAREHOUSE sin definir: usando los defaults del "
              "sandbox v5, que está MUERTO. Exportalos antes de correr esto en serio.")

    catalogo, esquema = crear_contenedores()
    subir_csvs(catalogo, esquema)

    paso("creación de las 8 tablas DESNUDAS")
    crear_todas()

    if verificar(catalogo, esquema):
        print(f"""
🟢 LISTO. Neptuno reconstruido en {catalogo}.{esquema} y las cifras coinciden.

Falta el único paso que la API no permite (formato `serialized_space` no documentado):
  1. Workspace → Genie → New → nombre «Ventas Neptuno»
  2. Warehouse: el de GENIE_WAREHOUSE
  3. Agregar las 8 tablas de {catalogo}.{esquema}
  4. NO pegar instrucciones todavía — el space crudo ES el Demo 0
  5. Ensayar «¿Cuál es el margen de la categoría Bebidas?» y confirmar que inventa el margen

Las capas 2/3/4 para pegar en vivo están en genie-space.md; las 1/5/6 en capas.sql.""")
    else:
        sys.exit("\n🔴 alguna cifra no coincide — NO uses esto en vivo sin revisar antes.")


if __name__ == "__main__":
    main()
