terraform {
  required_version = ">= 1.5"

  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.0"
    }
  }
}

# Autenticación por variables (o por las env vars DATABRICKS_HOST / DATABRICKS_TOKEN,
# o por el perfil del ~/.databrickscfg si preferís pasar `profile`).
provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}
