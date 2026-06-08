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
# Private, isolated network in AWS where all resources live, nothing enters or exits without explicit permission.

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}


# Resource 2: Public Subnet
# A subdivision of the VPC whose traffic is routed to the Internet Gateway, making resources inside it (like EC2) reachable from the internet.

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
# Physical connection between VPC and the internet

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

# Resource 4: Route Table
# Tells traffic where to go

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
    
  }

  tags = {
    Name = "Resonate-route-table"
  }
}

# Resource 5: Route Table Association
# Link the route table to your subnet

resource "aws_route_table_association" "main" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.main.id
}