#!/usr/bin/env python3
"""Hace la MISMA pregunta a los dos spaces (crudo y curado) y muestra el A/B."""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

# Databricks on AWS (14-ago-2026). Los ids del sandbox v5 ya no existen.
SPACES = {"CRUDO":  os.environ.get("GENIE_SPACE_CRUDO",  "01f1979ee629133bb42428d55e433cff"),
          "CURADO": os.environ.get("GENIE_SPACE_CURADO", "01f197a3c2c51e0493319fcefc5fb835")}
PROFILE = os.environ.get("GENIE_PROFILE", "webinar-aws")

def api(metodo, ruta, payload=None):
    cmd = ["databricks", "api", metodo, ruta, "-p", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:300])
    return json.loads(p.stdout or "{}")

def preguntar(par):
    etiqueta, space, texto = par
    try:
        r = api("post", f"/api/2.0/genie/spaces/{space}/start-conversation", {"content": texto})
        cid, mid = r["conversation_id"], r["message_id"]
        t0 = time.time()
        while time.time() - t0 < 180:
            m = api("get", f"/api/2.0/genie/spaces/{space}/conversations/{cid}/messages/{mid}")
            if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                txt, sql, datos = "", "", None
                for a in m.get("attachments", []) or []:
                    if "text" in a: txt = a["text"].get("content", "")
                    if "query" in a:
                        sql = a["query"].get("query", "")
                        txt = txt or a["query"].get("description", "")
                        aid = a.get("attachment_id")
                        if aid:
                            try:
                                res = api("get", f"/api/2.0/genie/spaces/{space}/conversations/"
                                                 f"{cid}/messages/{mid}/attachments/{aid}/query-result")
                                datos = res.get("statement_response", {}).get("result", {}).get("data_array")
                            except Exception: pass
                return (etiqueta, texto, txt.strip(), sql, datos)
            time.sleep(3)
        return (etiqueta, texto, "TIMEOUT", "", None)
    except Exception as e:
        return (etiqueta, texto, f"ERROR: {e}", "", None)

if __name__ == "__main__":
    preguntas = sys.argv[1:]
    tareas = [(et, sp, q) for q in preguntas for et, sp in SPACES.items()]
    res = {}
    with ThreadPoolExecutor(max_workers=len(tareas)) as ex:
        for et, q, txt, sql, datos in ex.map(preguntar, tareas):
            res.setdefault(q, {})[et] = (txt, sql, datos)
    for q in preguntas:
        print("\n" + "=" * 80)
        print(f"❓ {q}")
        for et in ("CRUDO", "CURADO"):
            txt, sql, datos = res[q][et]
            print(f"\n  ── {et} ──")
            print("  " + (txt[:500] or "(sin texto)").replace("\n", "\n  "))
            if datos: print(f"  📊 {datos}")
