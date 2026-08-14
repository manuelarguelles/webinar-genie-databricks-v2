# Contenedores de Unity Catalog para el dataset Neptuno del webinar de Genie.
#
# ALCANCE: catálogo, schema, volumen y (opcional) warehouse SQL.
# FUERA DE ALCANCE, a propósito:
#   - Las 8 tablas → las crea `bootstrap.py` con read_files() desde los CSVs del volumen,
#     DESNUDAS (sin COMMENT ni PK/FK) porque el Demo 0 necesita el Genie crudo. Terraform
#     no aporta nada ahí y complicaría el rollback entre ensayos.
#   - El Genie space → el provider NO tiene recurso `databricks_genie_space` (verificado
#     2026-08-13). Genie existe como recurso de Databricks Asset Bundles pero sólo en
#     direct mode, no por Terraform. Se crea por API con genie_client.create_space.

locals {
  catalog_name = var.create_catalog ? databricks_catalog.neptuno[0].name : var.catalog
  warehouse_id = var.create_warehouse ? databricks_sql_endpoint.webinar[0].id : null
}

resource "databricks_catalog" "neptuno" {
  count = var.create_catalog ? 1 : 0

  name    = var.catalog
  comment = "Neptuno — dataset del webinar «Databricks Genie en producción»"

  # Sólo se emite si la variable trae valor: con "" el catálogo usa el storage
  # por defecto del metastore.
  storage_root = var.managed_location != "" ? var.managed_location : null

  # El dataset se regenera entero desde los CSVs; no hay nada que proteger.
  force_destroy = true
}

resource "databricks_schema" "ventas" {
  catalog_name = local.catalog_name
  name         = var.schema
  comment      = "Ventas de Neptuno (Northwind en español, fechas +28 años)"

  force_destroy = true
}

resource "databricks_volume" "landing" {
  catalog_name = local.catalog_name
  schema_name  = databricks_schema.ventas.name
  name         = var.volume
  volume_type  = "MANAGED"
  comment      = "Aterrizaje de los 8 CSVs antes del CREATE TABLE"
}

resource "databricks_sql_endpoint" "webinar" {
  count = var.create_warehouse ? 1 : 0

  name                      = var.warehouse_name
  cluster_size              = var.warehouse_size
  auto_stop_mins            = var.warehouse_auto_stop_mins
  enable_serverless_compute = true

  tags {
    custom_tags {
      key   = "proyecto"
      value = "webinar-genie"
    }
  }
}
