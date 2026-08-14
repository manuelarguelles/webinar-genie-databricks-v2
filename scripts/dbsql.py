#!/usr/bin/env python3
"""Ejecuta SQL en un warehouse serverless vía Statement Execution API.

Destino configurable por entorno (el default sigue siendo el sandbox v5 histórico):
    export GENIE_WAREHOUSE=<warehouse_id>
    export GENIE_PROFILE=<perfil del ~/.databrickscfg>
"""
import json, os, subprocess, sys, time

WAREHOUSE = os.environ.get("GENIE_WAREHOUSE", "301ae960fc896653")
PROFILE = os.environ.get("GENIE_PROFILE", "sandbox-v5")

def sql(stmt, catalog=None, schema=None, silencioso=False):
    payload = {"warehouse_id": WAREHOUSE, "statement": stmt, "wait_timeout": "50s"}
    if catalog: payload["catalog"] = catalog
    if schema: payload["schema"] = schema
    p = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements", "-p", PROFILE,
         "--json", json.dumps(payload)],
        capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"CLI falló: {p.stderr[:500]}")
    r = json.loads(p.stdout)
    # esperar si quedó pendiente
    sid = r.get("statement_id")
    while r.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        time.sleep(3)
        p = subprocess.run(["databricks", "api", "get", f"/api/2.0/sql/statements/{sid}",
                            "-p", PROFILE], capture_output=True, text=True)
        r = json.loads(p.stdout)
    estado = r.get("status", {}).get("state")
    if estado != "SUCCEEDED":
        err = r.get("status", {}).get("error", {}).get("message", json.dumps(r)[:400])
        raise RuntimeError(f"{estado}: {err}")
    datos = r.get("result", {}).get("data_array", [])
    cols = [c["name"] for c in r.get("manifest", {}).get("schema", {}).get("columns", [])]
    if not silencioso and datos:
        print("  " + " | ".join(cols))
        for fila in datos[:50]:
            print("  " + " | ".join("" if v is None else str(v) for v in fila))
    return datos

if __name__ == "__main__":
    stmt = sys.stdin.read() if len(sys.argv) < 2 else sys.argv[1]
    for bloque in [b.strip() for b in stmt.split(";\n") if b.strip()]:
        print(f"\n▸ {bloque.splitlines()[0][:90]}")
        sql(bloque)
