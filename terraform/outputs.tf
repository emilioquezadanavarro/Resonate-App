output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.main.public_ip
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.endpoint
}