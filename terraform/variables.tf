# DB password

variable "db_password" {
  description = "The master password for the RDS instance"
  type        = string
  sensitive   = true
}