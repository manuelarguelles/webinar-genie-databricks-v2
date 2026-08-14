#!/usr/bin/env python3
"""Lanza preguntas al Genie space vía Conversation API, en paralelo, y devuelve
la respuesta + el SQL generado. Sirve para (a) probar el guion y (b) demostrar
la API en vivo."""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

SPACE = os.environ.get("GENIE_SPACE", "01f1979ee629133bb42428d55e433cff")
PROFILE = os.environ.get("GENIE_PROFILE", "webinar-aws")

def api(metodo, ruta, payload=None):
    cmd = ["databricks", "api", metodo, ruta, "-p", PROFILE]
    if payload is not None:
        cmd += ["--json", json.dumps(payload)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:400])
    return json.loads(p.stdout or "{}")

def preguntar(texto, timeout=180):
    r = api("post", f"/api/2.0/genie/spaces/{SPACE}/start-conversation",
            {"content": texto})
    cid = r["conversation_id"]; mid = r["message_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        m = api("get", f"/api/2.0/genie/spaces/{SPACE}/conversations/{cid}/messages/{mid}")
        estado = m.get("status")
        if estado in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
            texto_resp, sql, datos = "", "", None
            for a in m.get("attachments", []) or []:
                if "text" in a:
                    texto_resp = a["text"].get("content", "")
                if "query" in a:
                    sql = a["query"].get("query", "")
                    texto_resp = texto_resp or a["query"].get("description", "")
                    aid = a.get("attachment_id")
                    if aid:
                        try:
                            res = api("get", f"/api/2.0/genie/spaces/{SPACE}/conversations/"
                                             f"{cid}/messages/{mid}/attachments/{aid}/query-result")
                            sr = res.get("statement_response", {})
                            datos = sr.get("result", {}).get("data_array")
                        except Exception:
                            pass
            return {"pregunta": texto, "estado": estado, "respuesta": texto_resp,
                    "sql": sql, "datos": datos, "seg": round(time.time() - t0)}
        time.sleep(4)
    return {"pregunta": texto, "estado": "TIMEOUT"}

PREGUNTAS = [
    "¿Cuántos clientes activos tenemos?",
    "¿Cuál fue el ticket promedio el año pasado?",
    "¿Cuánto facturamos en total el año pasado?",
    "¿Cuántos productos tenemos a la venta?",
]

if __name__ == "__main__":
    preguntas = sys.argv[1:] or PREGUNTAS
    with ThreadPoolExecutor(max_workers=len(preguntas)) as ex:
        for r in ex.map(preguntar, preguntas):
            print("\n" + "=" * 78)
            print(f"❓ {r['pregunta']}   [{r['estado']}, {r.get('seg','?')}s]")
            print("-" * 78)
            print(r.get("respuesta", "").strip()[:700] or "(sin texto)")
            if r.get("datos"):
                print(f"\n📊 resultado: {r['datos']}")
            if r.get("sql"):
                print("\n```sql")
                print(r["sql"].strip())
                print("```")
