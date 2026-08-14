#!/usr/bin/env python3
"""Post-proceso de los CSVs de Neptuno:
1) desplaza las fechas +28 años (1996-1998 -> 2024-2026) para que el dataset
   sea contemporáneo: '+28' conserva bisiestos y día de la semana.
2) traduce las unidades de venta al español."""
import csv, re, os
from datetime import date

SHIFT = 28
D = "csv"

def shift(v):
    if not v: return v
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
    if not m: return v
    y, mo, d = map(int, m.groups())
    return date(y + SHIFT, mo, d).isoformat()

UNID = [
 (r"\bboxes\b","cajas"), (r"\bbox\b","caja"), (r"\bbottles\b","botellas"), (r"\bbottle\b","botella"),
 (r"\bjars\b","frascos"), (r"\bjar\b","frasco"), (r"\bpkgs\.?","paq."), (r"\bpkg\.?","paq."),
 (r"\bpieces\b","piezas"), (r"\bpiece\b","pieza"), (r"\bbags\b","bolsas"), (r"\bbag\b","bolsa"),
 (r"\bcans\b","latas"), (r"\bcan\b","lata"), (r"\btins\b","latas"), (r"\btin\b","lata"),
 (r"\bpcs\.?","uds."), (r"\brolls\b","rollos"), (r"\bloaves\b","panes"),
 (r"\bcups\b","vasos"), (r"\bjars\b","frascos"), (r"\bglasses\b","vasos"),
 (r"\bbarrels\b","barriles"), (r"\bpies\b","pasteles"),
 (r"\bcarton\b","cartón"), (r"\bwheel\b","rueda"), (r"\bwheels\b","ruedas"),
]
def unidades(v):
    for pat, rep in UNID:
        v = re.sub(pat, rep, v, flags=re.I)
    return v

def procesar(archivo, fn_por_col):
    ruta = os.path.join(D, archivo)
    filas = list(csv.DictReader(open(ruta, encoding="utf-8")))
    campos = list(filas[0].keys())
    for f in filas:
        for col, fn in fn_por_col.items():
            if col in f: f[col] = fn(f[col])
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos); w.writeheader(); w.writerows(filas)
    return len(filas)

n = procesar("pedidos.csv", {c: shift for c in ("FechaPedido","FechaEntrega","FechaEnvio")})
print(f"pedidos: {n} filas, fechas +{SHIFT} años")
n = procesar("empleados.csv", {c: shift for c in ("FechaNacimiento","FechaContratacion")})
print(f"empleados: {n} filas, fechas +{SHIFT} años")
n = procesar("productos.csv", {"CantidadPorUnidad": unidades})
print(f"productos: {n} filas, unidades traducidas")

# verificación
p = list(csv.DictReader(open("csv/pedidos.csv")))
fs = sorted(x["FechaPedido"] for x in p if x["FechaPedido"])
print(f"nuevo rango FechaPedido: {fs[0]} -> {fs[-1]}")
por_anio = {}
for x in p:
    por_anio[x["FechaPedido"][:4]] = por_anio.get(x["FechaPedido"][:4], 0) + 1
print("pedidos por año:", dict(sorted(por_anio.items())))
