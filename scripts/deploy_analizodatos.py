"""Prepara las dos páginas del webinar para publicar en analizodatos.com.

- Inyecta el mismo gate de clave que se usó en el taller de OpenClaw (mismo look,
  misma clave, misma tecla de "recordado" por localStorage).
- Corrige los enlaces relativos que sólo funcionan en local: en el server el deck
  y la consola viven en carpetas hermanas, no en ../guia/.
"""
import re, sys, pathlib

CLAVE = "16101991"
KEY = "webinar-databricks-ok"          # una sola clave abre las dos páginas
URL_CONSOLA = "https://analizodatos.com/webinar-ai-databricks-console/"
URL_SLIDES = "https://analizodatos.com/webinar-ai-databricks-slides/"

GATE = """
<style>
  #gate{position:fixed;inset:0;z-index:99999;display:grid;place-items:center;
        background:#05070e;color:#e8ecf8;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
  #gate .box{width:min(92vw,340px);display:grid;gap:14px;text-align:center}
  /* color explícito: si no, el h2 hereda el del deck y queda ilegible sobre el gate */
  #gate h2{margin:0;font-size:20px;font-weight:700;letter-spacing:-.01em;
        color:#e8ecf8;-webkit-text-fill-color:#e8ecf8;background:none;text-transform:none}
  #gate p{margin:0;font-size:14px;color:#93a0c0;line-height:1.5}
  #gate input{font:inherit;font-size:19px;letter-spacing:.32em;text-align:center;
        padding:13px 14px;border-radius:10px;border:1px solid #2c3550;
        background:#0c1120;color:#fff;outline:none}
  #gate input:focus{border-color:#6c5cff;box-shadow:0 0 0 3px rgba(108,92,255,.25)}
  #gate button{font:inherit;font-weight:650;font-size:15px;padding:12px;border:0;border-radius:10px;
        background:#6c5cff;color:#fff;cursor:pointer}
  #gate button:hover{filter:brightness(1.08)}
  #gate .err{color:#ff8095;font-size:13px;min-height:18px}
  body.locked{overflow:hidden}
</style>
<div id="gate">
  <div class="box">
    <h2>__TITULO__</h2>
    <p>Ingresa la clave que compartimos en el chat del webinar.</p>
    <input id="gk" type="password" inputmode="numeric" autocomplete="off" placeholder="••••••••" aria-label="Clave de acceso">
    <button id="gb" type="button">Entrar</button>
    <div class="err" id="ge" role="alert"></div>
  </div>
</div>
<script>
(function(){
  var CLAVE = "__CLAVE__", KEY = "__KEY__";
  var gate = document.getElementById('gate'),
      inp  = document.getElementById('gk'),
      err  = document.getElementById('ge');
  function abrir(){
    try { localStorage.setItem(KEY, "1"); } catch(e){}
    gate.remove();
    document.body.classList.remove('locked');
  }
  var recordado = false;
  try { recordado = localStorage.getItem(KEY) === "1"; } catch(e){}
  // Si ya está recordada, se abre y se SALE: si siguiera, intentaría enganchar
  // listeners a nodos que acaba de remover y tiraría TypeError en cada carga.
  if (recordado) { abrir(); return; }

  document.body.classList.add('locked');
  setTimeout(function(){ inp.focus(); }, 60);
  function probar(){
    if (inp.value.trim() === CLAVE) { abrir(); }
    else { err.textContent = "Clave incorrecta."; inp.select(); }
  }
  document.getElementById('gb').addEventListener('click', probar);
  inp.addEventListener('keydown', function(e){ if (e.key === 'Enter') probar(); });
})();
</script>
"""


def preparar(origen, destino, titulo, reemplazos):
    html = pathlib.Path(origen).read_text(encoding="utf-8")
    for viejo, nuevo in reemplazos:
        if viejo not in html:
            print(f"   ⚠ no encontrado para reemplazar: {viejo[:60]}")
        html = html.replace(viejo, nuevo)
    gate = (GATE.replace("__CLAVE__", CLAVE)
                .replace("__KEY__", KEY)
                .replace("__TITULO__", titulo))
    # el gate va al final del body para que el deck ya esté montado detrás
    if "</body>" in html:
        html = html.replace("</body>", gate + "\n</body>")
    else:
        html += gate
    pathlib.Path(destino).write_text(html, encoding="utf-8")
    print(f"   ✓ {destino}  ({len(html):,} bytes)")


BASE = "/Users/macdenix/clawd/webinar-genie-databricks-v2"
OUT = "/private/tmp/claude-501/-Users-macdenix-Library-CloudStorage-OneDrive-Personal-04--CLIENTES-APEX-DIGITAL-REPOSITORIOS/363a7dd6-772c-44f3-af17-80b598e3097f/scratchpad"

print("Preparando deck (reordenado)…")
preparar(f"{BASE}/deck/webinar-genie-v2-DECK-reordenado.html",
         f"{OUT}/slides-index.html",
         "Slides del webinar · acceso",
         [("var GUIA='../guia/taller-v2.html';", f"var GUIA='{URL_CONSOLA}';")])

print("Preparando consola (guía)…")
preparar(f"{BASE}/guia/taller-v2.html",
         f"{OUT}/console-index.html",
         "Consola del webinar · acceso",
         [])
