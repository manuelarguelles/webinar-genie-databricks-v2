#!/usr/bin/env python3
"""Northwind (northwind_psql) -> Neptuno ES: parsea los INSERT y emite CSVs
con nombres de tabla/columna y valores de dominio en español."""
import re, csv, os, io

SRC = "northwind.sql"
OUT = "csv"
os.makedirs(OUT, exist_ok=True)

# --- columnas origen, en el orden del CREATE TABLE ---
COLS = {
    "categories": ["category_id","category_name","description","picture"],
    "customers": ["customer_id","company_name","contact_name","contact_title","address","city","region","postal_code","country","phone","fax"],
    "employees": ["employee_id","last_name","first_name","title","title_of_courtesy","birth_date","hire_date","address","city","region","postal_code","country","home_phone","extension","photo","notes","reports_to","photo_path"],
    "order_details": ["order_id","product_id","unit_price","quantity","discount"],
    "orders": ["order_id","customer_id","employee_id","order_date","required_date","shipped_date","ship_via","freight","ship_name","ship_address","ship_city","ship_region","ship_postal_code","ship_country"],
    "products": ["product_id","product_name","supplier_id","category_id","quantity_per_unit","unit_price","units_in_stock","units_on_order","reorder_level","discontinued"],
    "shippers": ["shipper_id","company_name","phone"],
    "suppliers": ["supplier_id","company_name","contact_name","contact_title","address","city","region","postal_code","country","phone","fax","homepage"],
}

# --- mapeo tabla -> nombre ES ---
TABLA_ES = {
    "categories":"categorias", "customers":"clientes", "employees":"empleados",
    "order_details":"detalles_pedidos", "orders":"pedidos", "products":"productos",
    "shippers":"transportistas", "suppliers":"proveedores",
}

# --- mapeo columna -> nombre ES (por tabla) ---
COL_ES = {
 "categories":{"category_id":"IdCategoria","category_name":"NombreCategoria","description":"Descripcion"},
 "customers":{"customer_id":"IdCliente","company_name":"NombreCompania","contact_name":"NombreContacto",
   "contact_title":"CargoContacto","address":"Direccion","city":"Ciudad","region":"Region",
   "postal_code":"CodPostal","country":"Pais","phone":"Telefono","fax":"Fax"},
 "employees":{"employee_id":"IdEmpleado","last_name":"Apellidos","first_name":"Nombre","title":"Cargo",
   "title_of_courtesy":"Tratamiento","birth_date":"FechaNacimiento","hire_date":"FechaContratacion",
   "address":"Direccion","city":"Ciudad","region":"Region","postal_code":"CodPostal","country":"Pais",
   "home_phone":"TelefonoDomicilio","extension":"Extension","notes":"Notas","reports_to":"JefeId"},
 "order_details":{"order_id":"IdPedido","product_id":"IdProducto","unit_price":"PrecioUnidad",
   "quantity":"Cantidad","discount":"Descuento"},
 "orders":{"order_id":"IdPedido","customer_id":"IdCliente","employee_id":"IdEmpleado",
   "order_date":"FechaPedido","required_date":"FechaEntrega","shipped_date":"FechaEnvio",
   "ship_via":"IdTransportista","freight":"Cargo","ship_name":"NombreDestinatario",
   "ship_address":"DireccionDestinatario","ship_city":"CiudadDestinatario",
   "ship_region":"RegionDestinatario","ship_postal_code":"CodPostalDestinatario",
   "ship_country":"PaisDestinatario"},
 "products":{"product_id":"IdProducto","product_name":"NombreProducto","supplier_id":"IdProveedor",
   "category_id":"IdCategoria","quantity_per_unit":"CantidadPorUnidad","unit_price":"PrecioUnidad",
   "units_in_stock":"UnidadesEnExistencia","units_on_order":"UnidadesEnPedido",
   "reorder_level":"NivelNuevoPedido","discontinued":"Suspendido"},
 "shippers":{"shipper_id":"IdTransportista","company_name":"NombreCompania","phone":"Telefono"},
 "suppliers":{"supplier_id":"IdProveedor","company_name":"NombreCompania","contact_name":"NombreContacto",
   "contact_title":"CargoContacto","address":"Direccion","city":"Ciudad","region":"Region",
   "postal_code":"CodPostal","country":"Pais","phone":"Telefono","fax":"Fax","homepage":"PaginaWeb"},
}

# columnas que se descartan (binarios/rutas, ruido para la demo)
DROP = {"picture","photo","photo_path"}

CATEGORIAS = {
 "Beverages":"Bebidas", "Condiments":"Condimentos", "Confections":"Reposteria",
 "Dairy Products":"Lacteos", "Grains/Cereals":"Granos y Cereales",
 "Meat/Poultry":"Carnes y Aves", "Produce":"Frutas y Verduras", "Seafood":"Pescados y Mariscos",
}
CAT_DESC = {
 "Bebidas":"Bebidas gaseosas, cafes, tes, cervezas y licores",
 "Condimentos":"Salsas dulces y saladas, aderezos y condimentos",
 "Reposteria":"Postres, caramelos y panes dulces",
 "Lacteos":"Quesos y derivados de la leche",
 "Granos y Cereales":"Panes, galletas, pastas y cereales",
 "Carnes y Aves":"Carnes rojas y aves preparadas",
 "Frutas y Verduras":"Frutas secas y cuajada de frijol",
 "Pescados y Mariscos":"Algas y pescados",
}
PAISES = {
 "USA":"Estados Unidos","UK":"Reino Unido","Germany":"Alemania","France":"Francia","Spain":"España",
 "Brazil":"Brasil","Mexico":"Mexico","Canada":"Canada","Italy":"Italia","Sweden":"Suecia",
 "Austria":"Austria","Belgium":"Belgica","Denmark":"Dinamarca","Finland":"Finlandia",
 "Ireland":"Irlanda","Norway":"Noruega","Poland":"Polonia","Portugal":"Portugal",
 "Switzerland":"Suiza","Venezuela":"Venezuela","Argentina":"Argentina","Netherlands":"Paises Bajos",
 "Japan":"Japon","Singapore":"Singapur","Australia":"Australia",
}
CARGOS = {
 "Sales Representative":"Representante de Ventas","Owner":"Propietario",
 "Owner/Marketing Assistant":"Propietario/Asistente de Marketing",
 "Order Administrator":"Administrador de Pedidos","Sales Manager":"Gerente de Ventas",
 "Accounting Manager":"Gerente de Contabilidad","Assistant Sales Agent":"Agente de Ventas Asistente",
 "Marketing Manager":"Gerente de Marketing","Sales Associate":"Asociado de Ventas",
 "Sales Agent":"Agente de Ventas","Marketing Assistant":"Asistente de Marketing",
 "Vice President, Sales":"Vicepresidente de Ventas","Inside Sales Coordinator":"Coordinador de Ventas Internas",
 "Assistant Sales Representative":"Representante de Ventas Asistente",
 "Product Manager":"Gerente de Producto","Regional Account Rep.":"Representante Regional de Cuentas",
 "Coordinator Foreign Markets":"Coordinador de Mercados Externos",
 "Export Administrator":"Administrador de Exportaciones","Wholesale Account Agent":"Agente de Cuentas Mayoristas",
 "Sales Administrator":"Administrador de Ventas",
}
TRATAMIENTO = {"Ms.":"Sra.","Mrs.":"Sra.","Mr.":"Sr.","Dr.":"Dr."}
TRANSPORTISTAS = {"Speedy Express":"Expreso Veloz","United Package":"Paquetes Unidos","Federal Shipping":"Envios Federales"}

def parse_valores(s):
    """Divide la lista de VALUES respetando comillas simples escapadas ''."""
    out, buf, i, in_q = [], [], 0, False
    while i < len(s):
        c = s[i]
        if in_q:
            if c == "'":
                if i+1 < len(s) and s[i+1] == "'":
                    buf.append("'"); i += 2; continue
                in_q = False; i += 1; continue
            buf.append(c); i += 1; continue
        if c == "'":
            in_q = True; i += 1; continue
        if c == ",":
            out.append("".join(buf).strip()); buf = []; i += 1; continue
        buf.append(c); i += 1
    out.append("".join(buf).strip())
    return [None if v == "NULL" else v for v in out]

datos = {t: [] for t in COLS}
pat = re.compile(r"^INSERT INTO (\w+) VALUES \((.*)\);\s*$")
for linea in open(SRC, encoding="utf-8", errors="replace"):
    m = pat.match(linea)
    if not m: continue
    tabla, vals = m.group(1), m.group(2)
    if tabla not in COLS: continue
    datos[tabla].append(parse_valores(vals))

def limpiar_num(v):
    """real de postgres trae ruido float32 (9.80000019) -> redondear a 2/4 dec."""
    if v is None: return None
    try:
        f = float(v)
    except ValueError:
        return v
    return f"{round(f, 4):g}"

resumen = []
for tabla, filas in datos.items():
    cols = COLS[tabla]
    keep = [c for c in cols if c not in DROP]
    idx = [cols.index(c) for c in keep]
    dest = TABLA_ES[tabla]
    with open(f"{OUT}/{dest}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([COL_ES[tabla][c] for c in keep])
        n = 0
        for fila in filas:
            if len(fila) != len(cols):
                raise SystemExit(f"{tabla}: se esperaban {len(cols)} valores, llegaron {len(fila)}")
            r = [fila[i] for i in idx]
            d = dict(zip(keep, r))
            # --- traducción de valores de dominio ---
            if tabla == "categories":
                d["category_name"] = CATEGORIAS.get(d["category_name"], d["category_name"])
                d["description"] = CAT_DESC.get(d["category_name"], d["description"])
            if "country" in d:  d["country"]  = PAISES.get(d["country"], d["country"])
            if "ship_country" in d: d["ship_country"] = PAISES.get(d["ship_country"], d["ship_country"])
            if "contact_title" in d: d["contact_title"] = CARGOS.get(d["contact_title"], d["contact_title"])
            if tabla == "employees":
                d["title"] = CARGOS.get(d["title"], d["title"])
                d["title_of_courtesy"] = TRATAMIENTO.get(d["title_of_courtesy"], d["title_of_courtesy"])
                d["notes"] = None  # biografías en inglés: fuera
            if tabla == "shippers":
                d["company_name"] = TRANSPORTISTAS.get(d["company_name"], d["company_name"])
            # --- normalización numérica ---
            for c in ("unit_price","discount","freight"):
                if c in d: d[c] = limpiar_num(d[c])
            w.writerow([d[c] if d[c] is not None else "" for c in keep])
            n += 1
    resumen.append((dest, n, len(keep)))

print(f"{'tabla':22} {'filas':>7} {'cols':>5}")
for t, n, c in sorted(resumen):
    print(f"{t:22} {n:>7} {c:>5}")
