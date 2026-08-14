variable "databricks_host" {
  description = "URL del workspace, ej. https://dbc-xxxxxxxx-xxxx.cloud.databricks.com"
  type        = string
}

variable "databricks_token" {
  description = "PAT del workspace. Pasalo por TF_VAR_databricks_token, nunca en un .tfvars commiteado."
  type        = string
  sensitive   = true
}

variable "catalog" {
  description = "Catálogo Unity Catalog donde vive el dataset del webinar."
  type        = string
  default     = "neptuno"
}

variable "schema" {
  description = "Schema dentro del catálogo."
  type        = string
  default     = "ventas"
}

variable "volume" {
  description = "Volumen de aterrizaje para los CSVs."
  type        = string
  default     = "landing"
}

variable "managed_location" {
  description = <<-EOT
    MANAGED LOCATION del catálogo (ej. s3://bucket/path).
    Dejalo en "" para que el catálogo use el storage por defecto del metastore.
    ⚠️ Gotcha del build de julio: con metastore en Default Storage, crear el catálogo
    SIN managed location falla. Si el apply se queja, llená esta variable.
  EOT
  type        = string
  default     = ""
}

variable "create_catalog" {
  description = <<-EOT
    false = no crear catálogo; usar uno que ya existe (típico en workspaces serverless
    nuevos, donde ya viene `main` y no siempre se puede crear otro).
  EOT
  type        = bool
  default     = true
}

variable "create_warehouse" {
  description = "false = reusar el 'Serverless Starter Warehouse' que trae el workspace."
  type        = bool
  default     = false
}

variable "warehouse_name" {
  type    = string
  default = "webinar-genie-neptuno"
}

variable "warehouse_size" {
  description = "Neptuno son ~2.155 filas: el más chico sobra."
  type        = string
  default     = "2X-Small"
}

variable "warehouse_auto_stop_mins" {
  description = "El riesgo real de costo es dejar el warehouse encendido, no las queries."
  type        = number
  default     = 10
}
