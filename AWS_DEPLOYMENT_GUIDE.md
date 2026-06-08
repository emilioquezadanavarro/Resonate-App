# AWS Deployment Guide — Resonate App

This guide documents the full cloud deployment of the Resonate App to AWS,
covering Docker containerization, infrastructure provisioning with Terraform, and deployment to EC2 with RDS PostgreSQL.

---

## Architecture Overview

```
Internet
    ↓  (port 80)
EC2 t3.small (32.196.130.174)
    ↓
Docker Container
    ↓  Gunicorn → Flask → SQLAlchemy
RDS PostgreSQL (private subnet, port 5432)
    ↓  (accessible only from EC2 security group)
resonate database
```

**AWS Services Used:**
| Service | Purpose |
|---|---|
| EC2 (`t3.small`) | Virtual server running the Docker container |
| RDS PostgreSQL (`db.t3.micro`) | Managed relational database |
| VPC | Private isolated network for all resources |
| Subnets | Public (EC2) and private (RDS) network segments |
| Internet Gateway | Connects the VPC to the public internet |
| Route Table | Routes internet-bound traffic through the IGW |
| Security Groups | Firewall rules — port 80/22 for EC2, port 5432 (EC2 only) for RDS |

---

## Phase 1 — Docker

### Why Docker?
Docker packages the entire application (code, dependencies, runtime) into a portable image.
This guarantees the app runs identically on any machine — your Mac, a teammate's laptop, or an EC2 server.

Without Docker, deploying to EC2 would require manually installing Python, pip packages, and configuring the environment on the server. With Docker, you run one command.

### Key concepts
- **Image** — the static blueprint (like a recipe). Built once, stored in a registry.
- **Container** — the running instance of the image (like a meal). Ephemeral by nature.
- **Gunicorn** — production-grade WSGI server that replaces Flask's built-in dev server. Handles multiple concurrent requests.

### Dockerfile

```dockerfile
FROM python:3.13-slim              # Minimal Python base image
WORKDIR /app                       # Working directory inside container
COPY requirements.txt .            # Copy requirements first (layer caching)
RUN pip install --no-cache-dir -r requirements.txt   # Install dependencies
COPY . .                           # Copy app code
EXPOSE 5000                        # Document the port
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]  # Production server
```

**Why copy `requirements.txt` before `COPY . .`?**
Docker caches each layer. If you copy all files first, any code change invalidates the pip install cache — rebuilding takes 5 minutes every time. Copying requirements first means pip install is only re-run when dependencies actually change.

**Why `0.0.0.0:5000` in Gunicorn?**
Without this, Gunicorn binds to `127.0.0.1` (localhost inside the container), which is unreachable from outside. `0.0.0.0` means "accept connections from any network interface."

### .dockerignore
```
.env              # Never bake secrets into the image
.venv/            # Virtual environment — pip installs inside the container
chroma_db/        # Local vector store data
resonate.db       # Local SQLite database
.git/             # Git history
__pycache__/
.idea/
.DS_Store
```

### Commands

```bash
# Build the image locally
docker build -t resonate .

# Build for Linux/AMD64 (required when building on Apple Silicon for EC2)
docker buildx build --platform linux/amd64 -t username/resonate:latest --push .

# Run locally with environment variables
docker run -p 5000:5000 --env-file .env resonate

# Check running containers
docker ps

# View logs
docker logs $(docker ps -q) --tail 50

# View logs in real time
docker logs $(docker ps -q) -f

# Execute a command inside a running container
docker exec $(docker ps -q) python setup_db.py

# Stop and remove container
docker stop $(docker ps -q) && docker rm $(docker ps -aq)
```

---

## Phase 2 — Terraform

### Why Terraform?
Without Terraform, you provision AWS resources by clicking in the console. This is not reproducible, not version-controlled, and not reviewable by teammates.

Terraform lets you declare infrastructure as code (`.tf` files). You describe the desired end state, and Terraform calculates the minimum changes needed to reach it.

### Key concepts
- **Provider** — the plugin that talks to AWS (`hashicorp/aws`)
- **Resource** — a piece of infrastructure (`aws_vpc`, `aws_instance`, etc.)
- **State file** (`terraform.tfstate`) — Terraform's memory of what it created. Never commit this to Git.
- **`terraform plan`** — shows what will change, without changing anything. Always run before apply.
- **`terraform apply`** — creates/modifies real AWS resources.
- **`terraform destroy`** — tears everything down.

### Terraform commands

```bash
cd terraform

# Download AWS provider plugin (run once, or after provider changes)
terraform init

# Preview changes
terraform plan

# Apply changes (creates real AWS resources)
terraform apply

# Tear everything down
terraform destroy
```

### Infrastructure built (in order of dependency)

**1. VPC**
Your private isolated network in AWS. Everything lives inside it.
```hcl
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
```

**2. Public Subnet**
The subnet where EC2 lives. Public because it has a route to the Internet Gateway.
```hcl
resource "aws_subnet" "main" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
}
```

**3. Internet Gateway**
Connects the VPC to the internet. The front door — but it doesn't decide who enters (that's the Security Group).

**4. Route Table + Association**
Tells traffic where to go. Without this, the IGW exists but nothing uses it.
```hcl
route {
  cidr_block = "0.0.0.0/0"
  gateway_id = aws_internet_gateway.main.id
}
```
What makes a subnet "public" is not a checkbox — it's having a route to an Internet Gateway.

**5. Security Group — EC2**
Firewall rules for the EC2 instance:
- Port 80 inbound from anywhere → users access the app
- Port 22 inbound from anywhere → SSH management
- All outbound → app can call OpenAI, Gemini, etc.

**6. Security Group — RDS**
Firewall rules for the database:
- Port 5432 inbound from the EC2 security group **only** — not the internet
- This is enforced using `referenced_security_group_id` instead of a CIDR block

**7. Private Subnet (RDS)**
RDS lives here. No public IP, no route to the internet.
```hcl
resource "aws_subnet" "rds-main" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1b"
  map_public_ip_on_launch = false
}
```

**8. DB Subnet Group**
AWS requires this before creating RDS. It defines the pool of subnets RDS can use.
Minimum 2 subnets in 2 different AZs — AWS needs a fallback AZ for its managed operations.

**9. RDS Instance**
```hcl
resource "aws_db_instance" "main" {
  identifier           = "resonate-db"
  engine               = "postgres"
  engine_version       = "16"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  db_name              = "resonate"
  username             = "postgres"
  password             = var.db_password        # from variables.tf — never hardcoded
  publicly_accessible  = false
  skip_final_snapshot  = true
}
```

**Why RDS instead of PostgreSQL on EC2?**
- **Separation of concerns** — EC2 runs the app, RDS runs the database. Problems are isolated.
- **Managed service** — automated backups, patching, monitoring handled by AWS
- **Scalability** — scale app and database independently

**10. EC2 Instance**
```hcl
resource "aws_instance" "main" {
  ami           = "ami-00e801948462f718a"   # Amazon Linux 2023, us-east-1
  instance_type = "t3.small"               # 2GB RAM (t2.micro was too small for AI deps)
  key_name      = "resonate-key"

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y docker
    service docker start
    usermod -a -G docker ec2-user
  EOF
}
```

**`user_data`** — bash script that runs automatically on first boot. Installs Docker so the instance is ready without manual setup.

### variables.tf — passwords without hardcoding

```hcl
variable "db_password" {
  description = "The master password for the RDS instance"
  type        = string
  sensitive   = true   # Terraform never prints this value
}
```

When you run `terraform apply`, Terraform prompts for the value interactively. The password never touches any file.

---

## Phase 3 — SQLite → RDS Migration

### Why SQLite doesn't work in production
SQLite stores data in a single file (`resonate.db`). Inside a Docker container, that file is part of the container's ephemeral filesystem — it disappears every time the container restarts. Additionally, multiple containers can't share a SQLite file.

RDS solves this: the database lives completely separately from the app, persists independently, and can be reached by any container.

### Changes made

**`app/__init__.py`** — environment-based database config:
```python
database_url = os.environ.get('DATABASE_URL')
if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback to SQLite for local development
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
```

**`requirements.txt`** — PostgreSQL driver:
```
psycopg2-binary>=2.9.0
```
`psycopg2-binary` is the Python driver for PostgreSQL. Without it, SQLAlchemy cannot connect to RDS.

---

## Phase 4 — Deployment to EC2

### SSH into EC2
```bash
ssh -i ~/Downloads/cloud_project/resonate-key.pem ec2-user@32.196.130.174
```

### Run the container on EC2
```bash
docker run -d \
  --restart=always \
  -p 80:5000 \
  -e PYTHONUNBUFFERED=1 \
  -e OPENAI_API_KEY="..." \
  -e GEMINI_API_KEY="..." \
  -e TAVILY_API_KEY="..." \
  -e LANGFUSE_SECRET_KEY="..." \
  -e LANGFUSE_PUBLIC_KEY="..." \
  -e DATABASE_URL="postgresql://postgres:PASSWORD@resonate-db.co1aoisq2fyl.us-east-1.rds.amazonaws.com:5432/resonate" \
  emilioquezadanavarro/resonate:latest \
  gunicorn --bind 0.0.0.0:5000 --timeout 120 run:app
```

**Flags explained:**
- `-d` — detached mode, runs in background
- `--restart=always` — container restarts automatically on crash or EC2 reboot
- `-p 80:5000` — maps port 80 (standard HTTP) to container port 5000
- `-e KEY=value` — injects environment variables at runtime (secrets never in the image)
- `--timeout 120` — gives Gunicorn 120 seconds per request (AI agents are slow to initialize)
- `PYTHONUNBUFFERED=1` — forces Python to flush print statements immediately to Docker logs

### Initialize the database
```bash
docker exec $(docker ps -q) python setup_db.py
```

**Important:** `setup_db.py` uses `db.create_all()` which only creates tables that don't exist yet. To force a full schema reset (e.g., after changing column types), use:
```bash
docker exec $(docker ps -q) python -c "
from app import create_app
from app.database import db, Mood
app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    moods = ['Happy','Sad','Energetic','Calm','Anxious','Focused','Melancholic','Excited','Nostalgic','Lonely','Angry','Frustrated','Grateful','Bored','Confused']
    for label in moods:
        db.session.add(Mood(label=label))
    db.session.commit()
    print('Done')
"
```

---

## Key Design Decisions & Trade-offs

| Decision | Choice | Reason | Production alternative |
|---|---|---|---|
| Instance type | `t3.small` | 2GB RAM needed for AI deps | `t3.medium` or larger |
| RDS instance | `db.t3.micro` | Free tier eligible | `db.t3.small` or read replicas |
| Region | `us-east-1` | Already configured, most feature-complete | `eu-central-1` for European users |
| Multi-AZ RDS | No | Cost — doubles the price | Yes, for production |
| ChromaDB storage | Container filesystem | Simple for student project | Docker volume or managed vector DB |
| Secrets management | `-e` flags at runtime | Simple for student project | AWS Secrets Manager |
| `skip_final_snapshot` | `true` | Avoids S3 storage cost on destroy | `false` in production |

---

## Lessons Learned

**1. SQLite vs PostgreSQL strictness**
SQLite silently ignores column length constraints. PostgreSQL enforces them strictly.
A `VARCHAR(200)` column rejected music recommendations over 200 characters — worked locally, failed in production.

**2. Apple Silicon (ARM) vs EC2 (AMD64)**
Docker images built on M1/M2/M3 Macs are `arm64`. EC2 runs `linux/amd64`. Always build with:
```bash
docker buildx build --platform linux/amd64 ...
```

**3. AWS SSO token expiry**
Student accounts use SSO credentials that expire every ~8 hours. When Terraform fails with auth errors:
```bash
aws sso login
```

**4. `db.create_all()` does not alter existing tables**
Running `setup_db.py` after changing a column type does nothing to existing tables.
Use `db.drop_all()` + `db.create_all()` to force a full schema reset.

**5. Container ephemerality**
Any data written inside a container (ChromaDB vector store, SQLite file) is lost when the container stops.
This is why RDS is essential — the database lives outside the container lifecycle.
