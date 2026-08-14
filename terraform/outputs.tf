output "catalog" {
  description = "Catálogo efectivamente usado (creado o preexistente)."
  value       = local.catalog_name
}

output "schema" {
  value = databricks_schema.ventas.name
}

output "volume_path" {
  description = "Ruta del volumen donde bootstrap.py sube los CSVs."
  value       = "/Volumes/${local.catalog_name}/${databricks_schema.ventas.name}/${databricks_volume.landing.name}"
}

output "warehouse_id" {
  description = "null si create_warehouse = false; en ese caso usá el Serverless Starter del workspace."
  value       = local.warehouse_id
}

output "siguiente_paso" {
  description = "Cómo continuar después del apply."
  value       = <<-EOT
    export GENIE_PROFILE=<perfil>
    export GENIE_WAREHOUSE=${coalesce(local.warehouse_id, "<id del Serverless Starter>")}
    export GENIE_CATALOG=${local.catalog_name}
    export GENIE_SCHEMA=${databricks_schema.ventas.name}
    python3 ../bootstrap.py     # sube CSVs, crea las 8 tablas desnudas y verifica cifras
  EOT
}
