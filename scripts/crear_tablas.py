#!/usr/bin/env python3
"""Crea las tablas Delta de neptuno.ventas desde los CSVs del volumen.
DELIBERADAMENTE sin COMMENT ni PK/FK: el webinar arranca con el Genie crudo
y esas capas se agregan en vivo.

Destino configurable por entorno (defaults = los del webinar de julio):
    export GENIE_CATALOG=neptuno
    export GENIE_SCHEMA=ventas
"""
import os

from dbsql import sql

CAT = os.environ.get("GENIE_CATALOG", "neptuno")
ESQ = os.environ.get("GENIE_SCHEMA", "ventas")
VOL = f"/Volumes/{CAT}/{ESQ}/landing"

ESQUEMAS = {
 "categorias": "IdCategoria INT, NombreCategoria STRING, Descripcion STRING",
 "transportistas": "IdTransportista INT, NombreCompania STRING, Telefono STRING",
 "proveedores": ("IdProveedor INT, NombreCompania STRING, NombreContacto STRING, CargoContacto STRING, "
                 "Direccion STRING, Ciudad STRING, Region STRING, CodPostal STRING, Pais STRING, "
                 "Telefono STRING, Fax STRING, PaginaWeb STRING"),
 "clientes": ("IdCliente STRING, NombreCompania STRING, NombreContacto STRING, CargoContacto STRING, "
              "Direccion STRING, Ciudad STRING, Region STRING, CodPostal STRING, Pais STRING, "
              "Telefono STRING, Fax STRING"),
 "empleados": ("IdEmpleado INT, Apellidos STRING, Nombre STRING, Cargo STRING, Tratamiento STRING, "
               "FechaNacimiento DATE, FechaContratacion DATE, Direccion STRING, Ciudad STRING, "
               "Region STRING, CodPostal STRING, Pais STRING, TelefonoDomicilio STRING, "
               "Extension STRING, Notas STRING, JefeId INT"),
 "productos": ("IdProducto INT, NombreProducto STRING, IdProveedor INT, IdCategoria INT, "
               "CantidadPorUnidad STRING, PrecioUnidad DECIMAL(10,2), UnidadesEnExistencia INT, "
               "UnidadesEnPedido INT, NivelNuevoPedido INT, Suspendido INT"),
 "pedidos": ("IdPedido INT, IdCliente STRING, IdEmpleado INT, FechaPedido DATE, FechaEntrega DATE, "
             "FechaEnvio DATE, IdTransportista INT, Cargo DECIMAL(10,2), NombreDestinatario STRING, "
             "DireccionDestinatario STRING, CiudadDestinatario STRING, RegionDestinatario STRING, "
             "CodPostalDestinatario STRING, PaisDestinatario STRING"),
 "detalles_pedidos": ("IdPedido INT, IdProducto INT, PrecioUnidad DECIMAL(10,2), Cantidad INT, "
                      "Descuento DOUBLE"),
}

def crear_todas():
    for tabla, esquema in ESQUEMAS.items():
        print(f"▸ {tabla}")
        sql(f"DROP TABLE IF EXISTS {CAT}.{ESQ}.{tabla}")
        sql(f"""CREATE TABLE {CAT}.{ESQ}.{tabla} AS
                SELECT * FROM read_files('{VOL}/{tabla}.csv',
                  format => 'csv', header => true, schema => '{esquema}',
                  nullValue => '', mode => 'FAILFAST')""")

    print("\n--- conteo final ---")
    union = " UNION ALL ".join(
        f"SELECT '{t}' AS tabla, COUNT(*) AS filas FROM {CAT}.{ESQ}.{t}" for t in ESQUEMAS)
    return sql(f"SELECT * FROM ({union}) ORDER BY tabla")


if __name__ == "__main__":
    crear_todas()
