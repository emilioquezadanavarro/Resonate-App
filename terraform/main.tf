# Terraform block to define provider requirements and versions.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.92"
    }
  }

  required_version = ">= 1.2"
}

# Configure the AWS provider, setting the region for resource deployment.
provider "aws" {
  region = "us-east-1"
}

# Resource 1: VPC

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}


# Resource 2: Public Subnet

resource "aws_subnet" "main" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "Main"
  }
}

# Resource 3: Internet gateway

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}