# GNAF Web Application - AWS Cloud Infrastructure Architecture

**Version:** 1.0  
**Last Updated:** January 28, 2026  
**Application:** Australian Address Lookup & Property Research Platform

---

## Table of Contents

1. [Overview](#overview)
2. [High-Level Architecture](#high-level-aws-architecture)
3. [AWS Service Selection](#aws-service-selection)
4. [Network Architecture](#network-architecture)
5. [Security Configuration](#security-configuration)
6. [Auto Scaling Configuration](#auto-scaling-configuration)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [Deployment Process](#deployment-process)
9. [Cost Estimation](#cost-estimation)
10. [High Availability & Disaster Recovery](#high-availability--disaster-recovery)
11. [Performance Optimization](#performance-optimization)
12. [Security Best Practices](#security-best-practices)
13. [Maintenance Runbook](#maintenance-runbook)

---

## Overview

This document provides a production-ready AWS architecture for hosting the GNAF web application with high availability, scalability, and security. The architecture is designed to handle millions of address lookups while maintaining sub-2-second response times.

**Key Requirements:**
- Handle 15+ million address records
- Support concurrent users (100-1000+)
- Sub-2-second API response times
- 99.9% uptime SLA
- Secure data handling and encryption
- Cost-effective scaling

---

## High-Level AWS Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Internet Users                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Route 53 (DNS)                                    │
│  gnaf.yourdomain.com → CloudFront Distribution                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CloudFront CDN                                    │
│  - Global edge locations                                            │
│  - HTTPS/SSL termination (ACM certificate)                          │
│  - Cache static assets (CSS, JS, images)                            │
│  - DDoS protection (AWS Shield Standard)                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Application Load Balancer (ALB)                       │
│  - HTTPS listener (port 443)                                        │
│  - Health checks (/api/stats)                                       │
│  - SSL/TLS certificate (ACM)                                        │
│  - Cross-zone load balancing                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  EC2/ECS      │    │  EC2/ECS      │    │  EC2/ECS      │
│  Flask App    │    │  Flask App    │    │  Flask App    │
│  AZ-1a        │    │  AZ-1b        │    │  AZ-1c        │
│  (Gunicorn)   │    │  (Gunicorn)   │    │  (Gunicorn)   │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────┐
        │          VPC (10.0.0.0/16)                 │
        │                                            │
        │  ┌──────────────────────────────────────┐ │
        │  │   Public Subnets                     │ │
        │  │   - 10.0.1.0/24 (AZ-1a)              │ │
        │  │   - 10.0.2.0/24 (AZ-1b)              │ │
        │  │   - 10.0.3.0/24 (AZ-1c)              │ │
        │  │   (ALB, NAT Gateways)                │ │
        │  └──────────────────────────────────────┘ │
        │                                            │
        │  ┌──────────────────────────────────────┐ │
        │  │   Private Subnets (App)              │ │
        │  │   - 10.0.11.0/24 (AZ-1a)             │ │
        │  │   - 10.0.12.0/24 (AZ-1b)             │ │
        │  │   - 10.0.13.0/24 (AZ-1c)             │ │
        │  │   (EC2/ECS instances)                │ │
        │  └──────────────────────────────────────┘ │
        │                                            │
        │  ┌──────────────────────────────────────┐ │
        │  │   Private Subnets (Database)         │ │
        │  │   - 10.0.21.0/24 (AZ-1a)             │ │
        │  │   - 10.0.22.0/24 (AZ-1b)             │ │
        │  │   - 10.0.23.0/24 (AZ-1c)             │ │
        │  │   (RDS PostgreSQL)                   │ │
        │  └──────────┬───────────────────────────┘ │
        └─────────────┼──────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────────────┐
        │   RDS PostgreSQL with PostGIS           │
        │   - Primary: AZ-1a (db.r6g.2xlarge)     │
        │   - Standby: AZ-1b (Multi-AZ)           │
        │   - Storage: 500GB GP3 SSD (10,000 IOPS)│
        │   - Automated backups (7-day retention) │
        │   - Read replicas (optional)            │
        └─────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      Supporting Services                             │
├─────────────────────────────────────────────────────────────────────┤
│  S3 Buckets:                                                         │
│  - gnaf-backups (database backups, lifecycle to Glacier)            │
│  - gnaf-static-assets (optional: hero images, fonts)                │
│  - gnaf-logs (ALB/CloudFront access logs)                           │
│                                                                      │
│  ElastiCache Redis (optional):                                      │
│  - cache.r6g.large (for API response caching)                       │
│  - Multi-AZ with automatic failover                                 │
│                                                                      │
│  Secrets Manager:                                                    │
│  - Database credentials                                             │
│  - API keys                                                          │
│                                                                      │
│  CloudWatch:                                                         │
│  - Application logs (from EC2/ECS)                                  │
│  - Database metrics (RDS)                                           │
│  - ALB metrics                                                       │
│  - Custom metrics (API latency)                                     │
│  - Alarms (CPU, memory, errors)                                     │
│                                                                      │
│  Auto Scaling:                                                       │
│  - Target tracking: CPU 70%                                         │
│  - Min instances: 2                                                  │
│  - Max instances: 10                                                 │
│  - Scale-out: +2 instances when CPU >70% for 5 min                 │
│  - Scale-in: -1 instance when CPU <30% for 10 min                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## AWS Service Selection

### Compute Layer

#### Option 1: EC2 Auto Scaling Group (Recommended for flexibility)

**Instance Type:** t3.large or t3.xlarge (2-4 vCPU, 8-16 GB RAM)

**Pros:**
- Full control over instance configuration
- Easy to debug and troubleshoot
- Direct SSH access
- Simple deployment process

**Cons:**
- Manual OS patching required
- More operational overhead

**Setup:**
```bash
# User Data script for EC2 launch
#!/bin/bash
yum update -y
yum install -y python3.13 git postgresql15

# Clone application
cd /opt
git clone <repo_url> gnaf-app
cd gnaf-app

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start application with systemd
cp gnaf-webapp.service /etc/systemd/system/
systemctl enable gnaf-webapp
systemctl start gnaf-webapp
```

#### Option 2: ECS Fargate (Recommended for containerization)

**Task Definition:**
- CPU: 2048 (2 vCPU)
- Memory: 4096 MB (4 GB)
- Container: Flask app with Gunicorn

**Pros:**
- Serverless container management
- Automatic scaling
- No EC2 instance management
- Rolling deployments

**Cons:**
- Slightly higher cost per vCPU
- Less flexibility for debugging

#### Option 3: Elastic Beanstalk (Easiest deployment)

**Environment:** Python 3.13 platform

**Pros:**
- Simplest deployment (just upload zip)
- Automatic load balancing
- Built-in monitoring
- Managed updates

**Cons:**
- Less control over infrastructure
- May incur additional costs

---

### Database Layer

#### RDS PostgreSQL with PostGIS

**Configuration:**
- **Engine:** PostgreSQL 16.x
- **Instance Class:** db.r6g.2xlarge (8 vCPU, 64 GB RAM)
  - Dev/Test: db.t3.large (2 vCPU, 8 GB RAM)
- **Storage:** 500 GB GP3 SSD
  - IOPS: 10,000 (provisioned)
  - Throughput: 500 MB/s
- **Multi-AZ:** Enabled (for high availability)
- **Read Replicas:** 1-2 (for read-heavy workloads)
- **Backup:**
  - Automated daily backups (7-day retention)
  - Manual snapshots before major updates
  - Backup window: 02:00-03:00 UTC
- **Maintenance Window:** Sunday 03:00-04:00 UTC

**PostGIS Extension:**
```sql
-- Run after RDS creation
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
```

**Parameter Group Settings:**
```ini
shared_buffers = 16GB                   # 25% of 64GB RAM
effective_cache_size = 48GB             # 75% of 64GB RAM
maintenance_work_mem = 2GB
work_mem = 256MB
max_connections = 200
```

---

### Content Delivery

#### CloudFront Distribution

**Cache Behaviors:**
- `/static/*` → Cache everything (TTL: 7 days)
- `/api/*` → No caching (pass through to ALB)
- `/` → Cache HTML (TTL: 1 hour)

**Origin Settings:**
- Primary: ALB (custom origin)
- Backup: S3 bucket (for maintenance page)

**SSL Certificate:**
- ACM certificate for `gnaf.yourdomain.com`
- Minimum TLS version: 1.2

**WAF (Optional):**
- AWS WAF rules for DDoS protection
- Rate limiting: 2000 requests/5 min per IP
- Geo-blocking (if needed)

---

### Storage

#### S3 Buckets

**1. gnaf-backups:**
- Purpose: Database backups, GNAF data archive
- Lifecycle: Move to Glacier after 30 days
- Versioning: Enabled
- Encryption: AES-256 (SSE-S3)

**2. gnaf-static-assets (optional):**
- Purpose: Host hero images locally instead of Unsplash
- CloudFront origin for static assets
- Public read access

**3. gnaf-logs:**
- Purpose: ALB, CloudFront access logs
- Lifecycle: Delete after 90 days
- Compression: Enabled

---

### Caching (Optional)

#### ElastiCache Redis

**Configuration:**
- **Node Type:** cache.r6g.large (2 vCPU, 13 GB RAM)
- **Cluster Mode:** Disabled (for simplicity)
- **Multi-AZ:** Enabled
- **Replicas:** 1 read replica

**Use Cases:**
- Cache API responses (suburb lists, stats)
- Session storage (if adding user accounts)
- Rate limiting counters

**Flask Integration:**
```python
import redis
from functools import wraps

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=6379,
    decode_responses=True
)

def cache_response(ttl=300):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cache_key = f"{f.__name__}:{str(args)}:{str(kwargs)}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            result = f(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@app.route('/api/stats')
@cache_response(ttl=3600)  # Cache for 1 hour
def get_stats():
    # ... database query ...
```

---

## Network Architecture

### VPC Configuration

**CIDR Block:** 10.0.0.0/16

**Subnets:**

| Tier | AZ | CIDR | Purpose |
|------|-----|------|---------|
| Public | us-east-1a | 10.0.1.0/24 | ALB, NAT Gateway |
| Public | us-east-1b | 10.0.2.0/24 | ALB, NAT Gateway |
| Public | us-east-1c | 10.0.3.0/24 | ALB, NAT Gateway |
| Private (App) | us-east-1a | 10.0.11.0/24 | EC2/ECS |
| Private (App) | us-east-1b | 10.0.12.0/24 | EC2/ECS |
| Private (App) | us-east-1c | 10.0.13.0/24 | EC2/ECS |
| Private (DB) | us-east-1a | 10.0.21.0/24 | RDS Primary |
| Private (DB) | us-east-1b | 10.0.22.0/24 | RDS Standby |
| Private (DB) | us-east-1c | 10.0.23.0/24 | RDS Read Replica |

**Route Tables:**

- **Public:** Routes to Internet Gateway
- **Private:** Routes to NAT Gateway (for outbound internet)
- **Database:** No internet access (isolated)

**NAT Gateways:**
- One per AZ for high availability
- Elastic IP for each NAT Gateway

---

## Security Configuration

### Security Groups

#### 1. ALB Security Group (sg-alb)
- Inbound: 443 (HTTPS) from 0.0.0.0/0
- Inbound: 80 (HTTP) from 0.0.0.0/0 (redirect to 443)
- Outbound: All traffic to App SG

#### 2. Application Security Group (sg-app)
- Inbound: 5000 from ALB SG
- Outbound: 5432 to DB SG
- Outbound: 443 to 0.0.0.0/0 (for API calls)
- Outbound: 6379 to Redis SG (if using ElastiCache)

#### 3. Database Security Group (sg-db)
- Inbound: 5432 from App SG only
- Outbound: None

#### 4. Redis Security Group (sg-redis)
- Inbound: 6379 from App SG only
- Outbound: None

---

### IAM Roles

#### EC2/ECS Task Role:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::gnaf-backups/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:gnaf/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/gnaf/*"
    }
  ]
}
```

---

### Secrets Manager

Store sensitive credentials:
```json
{
  "DB_HOST": "gnaf-db.xxxxx.us-east-1.rds.amazonaws.com",
  "DB_PORT": "5432",
  "DB_NAME": "gnaf_db",
  "DB_USER": "gnaf_admin",
  "DB_PASSWORD": "SecureRandomPassword123!",
  "REDIS_HOST": "gnaf-redis.xxxxx.cache.amazonaws.com"
}
```

**Retrieve in Flask:**
```python
import boto3
import json
from botocore.exceptions import ClientError

def get_secret():
    secret_name = "gnaf/database"
    region_name = "us-east-1"
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e
    
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)

# Usage
secrets = get_secret()
DB_HOST = secrets['DB_HOST']
DB_PASSWORD = secrets['DB_PASSWORD']
```

---

## Auto Scaling Configuration

### EC2 Auto Scaling Group

**Launch Template:**
- AMI: Amazon Linux 2023
- Instance Type: t3.large
- IAM Role: EC2-GNAF-Role
- Security Groups: sg-app
- User Data: Install and start Flask app

**Scaling Policies:**

**Target Tracking:**
- Metric: Average CPU Utilization
- Target: 70%
- Cooldown: 300 seconds

**Step Scaling (optional):**
```
CPU > 80% for 5 min → Add 2 instances
CPU > 90% for 5 min → Add 4 instances
CPU < 30% for 10 min → Remove 1 instance
```

**Scheduled Scaling (optional):**
```
# Business hours (9 AM - 6 PM AEST)
Min: 4 instances
Max: 10 instances

# Off-hours
Min: 2 instances
Max: 6 instances
```

---

### ECS Auto Scaling

**Service Auto Scaling:**
- Target: 70% CPU
- Min tasks: 2
- Max tasks: 10
- Scale-out cooldown: 60 seconds
- Scale-in cooldown: 300 seconds

**Task Definition:**
```json
{
  "family": "gnaf-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "gnaf-flask",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/gnaf:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "FLASK_ENV", "value": "production"}
      ],
      "secrets": [
        {
          "name": "DB_HOST",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:gnaf/db:DB_HOST::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/aws/ecs/gnaf",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "flask"
        }
      }
    }
  ]
}
```

---

## Monitoring & Alerting

### CloudWatch Alarms

| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| High CPU | EC2/ECS CPU | >80% for 5 min | SNS notification |
| High Memory | Memory Utilization | >85% for 5 min | SNS notification |
| DB Connections | RDS Connections | >180 | SNS notification |
| DB CPU | RDS CPU | >75% for 10 min | SNS notification |
| 5xx Errors | ALB 5xx count | >50/5 min | SNS notification + scale out |
| Slow Queries | API Latency | >3s (p95) | SNS notification |

---

### CloudWatch Dashboards

**Create dashboard with:**
- ALB request count, latency, error rates
- EC2/ECS CPU, memory, network
- RDS CPU, connections, read/write IOPS
- Application logs (errors, warnings)

**CloudWatch Logs Insights Queries:**

**Find errors:**
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

**API latency analysis:**
```
fields @timestamp, status, latency
| filter url like /api/
| stats avg(latency), max(latency), p95(latency) by bin(5m)
```

---

### X-Ray (Optional)

**Distributed tracing for:**
- API call flow visualization
- Identify slow database queries
- Performance bottleneck analysis
- Service map generation

**Flask integration:**
```python
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

app = Flask(__name__)
xray_recorder.configure(service='GNAF-API')
XRayMiddleware(app, xray_recorder)
```

---

## Deployment Process

### Step 1: Infrastructure Setup (Terraform)

**main.tf:**
```hcl
provider "aws" {
  region = "us-east-1"
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "gnaf-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnets = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  database_subnets = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
  
  enable_nat_gateway = true
  enable_dns_hostnames = true
}

# RDS PostgreSQL
module "rds" {
  source = "terraform-aws-modules/rds/aws"
  
  identifier = "gnaf-db"
  engine = "postgres"
  engine_version = "16.1"
  instance_class = "db.r6g.2xlarge"
  allocated_storage = 500
  storage_type = "gp3"
  iops = 10000
  
  db_name  = "gnaf_db"
  username = "postgres"
  password = random_password.db_password.result
  
  multi_az = true
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name = module.vpc.database_subnet_group_name
  
  backup_retention_period = 7
  backup_window = "02:00-03:00"
  maintenance_window = "sun:03:00-sun:04:00"
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  tags = {
    Environment = "production"
    Application = "GNAF"
  }
}

# ALB
module "alb" {
  source = "terraform-aws-modules/alb/aws"
  
  name = "gnaf-alb"
  load_balancer_type = "application"
  
  vpc_id = module.vpc.vpc_id
  subnets = module.vpc.public_subnets
  security_groups = [aws_security_group.alb.id]
  
  target_groups = [
    {
      name_prefix      = "gnaf-"
      backend_protocol = "HTTP"
      backend_port     = 5000
      target_type      = "ip"
      health_check = {
        enabled = true
        path    = "/api/stats"
        matcher = "200"
      }
    }
  ]
  
  https_listeners = [
    {
      port               = 443
      protocol           = "HTTPS"
      certificate_arn    = aws_acm_certificate.gnaf.arn
      target_group_index = 0
    }
  ]
}
```

---

### Step 2: Database Initialization

```bash
# Connect to RDS instance (from bastion host or EC2 in private subnet)
psql -h gnaf-db.xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d gnaf_db

# Create schema and extensions
CREATE SCHEMA IF NOT EXISTS gnaf;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

# Load GNAF data (from EC2 instance)
# Transfer data to EC2 first
aws s3 cp s3://gnaf-backups/gnaf-data.zip /data/
unzip /data/gnaf-data.zip -d /data/gnaf/

# Run loader
python3 load_psv_to_postgres.py /data/gnaf/
```

---

### Step 3: Application Deployment

#### Option A: EC2 with CodeDeploy

**appspec.yml:**
```yaml
version: 0.0
os: linux
files:
  - source: /
    destination: /opt/gnaf-app
hooks:
  ApplicationStop:
    - location: scripts/stop_app.sh
      timeout: 300
  ApplicationStart:
    - location: scripts/start_app.sh
      timeout: 300
  ValidateService:
    - location: scripts/validate.sh
      timeout: 300
```

**scripts/start_app.sh:**
```bash
#!/bin/bash
cd /opt/gnaf-app/webapp
source /opt/gnaf-app/venv/bin/activate
systemctl start gnaf-webapp
```

#### Option B: ECS with ECR

**Build and push Docker image:**
```bash
# Build image
docker build -t gnaf-app .

# Tag image
docker tag gnaf-app:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/gnaf:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Push image
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/gnaf:latest

# Update ECS service
aws ecs update-service --cluster gnaf-cluster --service gnaf-service --force-new-deployment
```

---

### Step 4: DNS Configuration

**Route 53:**
```bash
# Create hosted zone
aws route53 create-hosted-zone --name yourdomain.com

# Create A record pointing to CloudFront
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "gnaf.yourdomain.com",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z2FDTNDATAQYW2",
        "DNSName": "d123456.cloudfront.net",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
```

---

## Cost Estimation

### Monthly Cost Breakdown (Production)

| Service | Configuration | Monthly Cost (USD) |
|---------|---------------|-------------------|
| **RDS PostgreSQL** | db.r6g.2xlarge Multi-AZ, 500GB GP3 | $850 |
| **EC2 Auto Scaling** | 3x t3.large (avg), Reserved | $160 |
| **ALB** | Standard, 1M requests | $25 |
| **CloudFront** | 1TB data transfer, 10M requests | $85 |
| **S3** | 100GB storage, 1TB transfer | $25 |
| **ElastiCache Redis** | cache.r6g.large Multi-AZ | $200 |
| **NAT Gateway** | 3x NAT, 1TB data | $135 |
| **CloudWatch** | Logs, metrics, alarms | $30 |
| **Route 53** | Hosted zone, queries | $10 |
| **Data Transfer** | Inter-AZ, out to internet | $50 |
| **Total** | | **~$1,570/month** |

---

### Cost Optimization Tips

**1. Use Reserved Instances:**
- RDS: 1-year Reserved → Save 40% (~$340/month)
- EC2: 1-year Reserved → Save 35% (~$56/month)
- **Total savings: ~$350/month**

**2. Right-sizing:**
- Start with smaller instances (t3.medium for app, db.t3.large for DB)
- Scale up based on actual usage
- Use RDS Performance Insights to optimize
- **Potential savings: $200-300/month**

**3. S3 Lifecycle:**
- Move backups to Glacier after 30 days
- Save ~70% on backup storage
- **Savings: $15-20/month**

**4. CloudFront Optimization:**
- Cache more aggressively
- Reduce origin requests
- Consider CloudFront Savings Bundle
- **Savings: $20-30/month**

**5. Dev/Test Environment:**
- Use smaller instance types
- Single-AZ RDS
- Stop instances during off-hours (nights/weekends)
- **Cost: ~$300/month (vs $1,570 for production)**

**Optimized Production Cost:** ~$1,220/month (with Reserved Instances)

---

## High Availability & Disaster Recovery

### Service Level Objectives

- **Availability:** 99.9% (8.76 hours downtime/year)
- **RTO (Recovery Time Objective):** 15 minutes
- **RPO (Recovery Point Objective):** 5 minutes

---

### High Availability Strategy

**1. Multi-AZ Deployment:**
- Application: 3 AZs (us-east-1a, 1b, 1c)
- Database: Multi-AZ automatic failover
- ALB: Cross-zone load balancing
- NAT: One per AZ (no single point of failure)

**2. Auto-healing:**
- ALB health checks every 30 seconds
- Auto Scaling replaces unhealthy instances
- RDS automatic failover (60-120 seconds)
- ECS task auto-restart on failure

**3. Data Redundancy:**
- RDS Multi-AZ synchronous replication
- S3 standard storage (99.999999999% durability)
- EBS snapshots (daily)

---

### Disaster Recovery Scenarios

#### Scenario 1: Single AZ Failure
- **Detection:** Automatic (ALB health checks)
- **Action:** Automatic traffic rerouting to healthy AZs
- **Impact:** None (transparent to users)
- **Recovery Time:** Immediate

#### Scenario 2: Database Failure
- **Detection:** Automatic (RDS monitoring)
- **Action:** Automatic failover to standby
- **Impact:** 60-120 seconds of downtime
- **Recovery Time:** 2 minutes

#### Scenario 3: Region Failure
- **Detection:** Manual monitoring
- **Action:** 
  1. Restore latest RDS snapshot in another region
  2. Deploy application stack via Terraform
  3. Update Route 53 DNS
- **Impact:** 2-4 hours downtime
- **Recovery Time:** 2-4 hours
- **Cost:** Active-passive DR adds ~30% to costs

#### Scenario 4: Data Corruption
- **Detection:** Manual (user reports or monitoring)
- **Action:** Point-in-time restore from RDS backup
- **Impact:** Up to 5 minutes of data loss (RPO)
- **Recovery Time:** 30-60 minutes

---

### Backup Strategy

**RDS Automated Backups:**
- Daily snapshots (7-day retention)
- Transaction logs (5-minute point-in-time recovery)
- Backup window: 02:00-03:00 UTC

**Manual Snapshots:**
- Before major updates/deployments
- Monthly full backups (12-month retention)
- Copy to S3 for long-term storage

**Application Backups:**
- S3 bucket for GNAF source data
- S3 lifecycle to Glacier after 30 days
- Cross-region replication (optional)

---

## Performance Optimization

### Database Optimization

**1. Connection Pooling:**
```python
from psycopg2 import pool

db_pool = pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

def get_db_connection():
    return db_pool.getconn()

def return_db_connection(conn):
    db_pool.putconn(conn)
```

**2. Read Replicas:**
- Create 1-2 read replicas
- Route read queries to replicas
- Use Route 53 weighted routing
- Reduce load on primary database

**3. Query Optimization:**
- Enable pg_stat_statements extension
- Monitor slow queries in CloudWatch
- Add missing indexes identified by query plans
- Use EXPLAIN ANALYZE for query tuning

**4. RDS Performance Insights:**
- Identify top SQL statements
- Track wait events
- Optimize connection management

---

### Application Optimization

**1. Static Asset Delivery:**
- Serve CSS/JS/images from CloudFront
- Enable Gzip/Brotli compression
- Set far-future cache headers (1 year)
- Minimize and bundle JS/CSS

**2. API Response Caching:**
```python
# Cache frequently accessed data in Redis
@cache_response(ttl=3600)  # 1 hour
def get_stats():
    # Expensive database query
    pass

@cache_response(ttl=86400)  # 24 hours
def get_suburbs_by_state(state):
    # Static data, rarely changes
    pass
```

**3. Database Query Optimization:**
```python
# Use DISTINCT ON instead of multiple queries
# Batch queries where possible
# Limit result sets (pagination)

# Example: Paginated results
def get_addresses(page=1, per_page=100):
    offset = (page - 1) * per_page
    query = """
        SELECT * FROM gnaf.address_detail
        WHERE date_retired IS NULL
        LIMIT %s OFFSET %s
    """
    return execute_query(query, (per_page, offset))
```

**4. Async Operations (Optional):**
- Use Celery + SQS for background tasks
- Offload heavy computations
- Generate reports asynchronously
- Send email notifications via SES

---

### CloudFront Optimization

**Cache Policies:**
```json
{
  "/static/*": {
    "TTL": 604800,
    "Compress": true,
    "QueryStringBehavior": "none"
  },
  "/": {
    "TTL": 3600,
    "Compress": true,
    "QueryStringBehavior": "all"
  },
  "/api/*": {
    "TTL": 0,
    "Compress": false,
    "QueryStringBehavior": "all"
  }
}
```

---

## Security Best Practices

### 1. Network Security

**VPC Best Practices:**
- Private subnets for app and database (no public IPs)
- NAT Gateway for outbound internet only
- VPC Flow Logs enabled (monitor traffic)
- Network ACLs for additional layer of security

**Security Groups:**
- Follow principle of least privilege
- Only allow required ports
- Use security group IDs (not CIDR) for internal traffic

---

### 2. Data Encryption

**Encryption at Rest:**
- RDS: Enable encryption with AWS KMS
- EBS: Encrypt all volumes
- S3: Server-side encryption (SSE-S3 or SSE-KMS)

**Encryption in Transit:**
- ALB: HTTPS/TLS 1.2+ only
- RDS: Force SSL connections
- S3: HTTPS only bucket policy

**RDS SSL Connection:**
```python
import ssl

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    sslmode='require',
    sslrootcert='/path/to/rds-ca-cert.pem'
)
```

---

### 3. Access Control

**IAM Best Practices:**
- Use IAM roles (not access keys)
- Principle of least privilege
- Enable MFA for root account
- Rotate credentials regularly
- Use IAM policies for fine-grained control

**SSM Session Manager:**
```bash
# No SSH keys needed, uses IAM
aws ssm start-session --target i-1234567890abcdef
```

---

### 4. Application Security

**Flask Security Headers:**
```python
@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' https://images.unsplash.com; font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self' 'unsafe-inline';"
    return response
```

**Input Validation:**
```python
from flask import request, abort
import re

@app.route('/api/search/suburbs')
def search_suburbs():
    query = request.args.get('q', '')
    
    # Validate input
    if not re.match(r'^[a-zA-Z0-9\s\-]+$', query):
        abort(400, 'Invalid search query')
    
    if len(query) > 100:
        abort(400, 'Query too long')
    
    # Use parameterized queries (prevent SQL injection)
    results = execute_query(
        "SELECT * FROM gnaf.locality WHERE name ILIKE %s",
        (f'%{query}%',)
    )
    return jsonify(results)
```

**Rate Limiting:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/api/search/suburbs")
@limiter.limit("10 per minute")
def search_suburbs():
    # API endpoint
    pass
```

---

### 5. Compliance & Auditing

**AWS Services:**
- **CloudTrail:** All API calls logged
- **Config:** Track configuration changes
- **GuardDuty:** Threat detection
- **Security Hub:** Centralized security findings
- **IAM Access Analyzer:** Identify unintended access

**Compliance Standards:**
- GDPR compliance (if handling EU data)
- SOC 2 (with AWS compliance programs)
- PCI DSS (if handling payment data)

---

## Maintenance Runbook

### Daily Tasks (Automated)

- CloudWatch alarms monitoring
- RDS automated backups
- Log aggregation to S3
- Cost and usage reports

---

### Weekly Tasks

**Monday:**
- Review CloudWatch dashboards
- Check for failed deployments
- Review security group changes

**Friday:**
- Review AWS Cost Explorer
- Check for unused resources
- Review CloudWatch Logs for errors

---

### Monthly Tasks

- **Performance Review:**
  - Analyze RDS Performance Insights
  - Review slow queries (>2s)
  - Check Auto Scaling metrics
  - Optimize CloudFront cache hit ratio

- **Security Review:**
  - Review IAM permissions
  - Check for exposed resources
  - Update security patches (OS, Python)
  - Review GuardDuty findings

- **Cost Optimization:**
  - Identify unused resources (EBS, EIPs)
  - Right-size instances based on metrics
  - Review Reserved Instance utilization
  - Clean up old snapshots/backups

---

### Quarterly Tasks

- **Database Maintenance:**
  - VACUUM and ANALYZE tables
  - Review and optimize indexes
  - Update RDS parameter groups
  - Test failover to standby

- **Disaster Recovery Drill:**
  - Restore from backup to test environment
  - Verify all data restored correctly
  - Document recovery time
  - Update runbooks

- **Capacity Planning:**
  - Review 3-month growth trends
  - Plan for traffic spikes
  - Estimate future costs
  - Update Auto Scaling policies

---

### Annual Tasks

- **Infrastructure Review:**
  - Update Terraform configurations
  - Review architecture for improvements
  - Evaluate new AWS services
  - Plan major upgrades (PostgreSQL version)

- **GNAF Data Update:**
  - Download latest GNAF release
  - Test in dev environment
  - Schedule production update
  - Verify data integrity

- **Security Audit:**
  - Third-party penetration testing
  - Review compliance certifications
  - Update security policies
  - Rotate all credentials

- **Financial Review:**
  - Renew Reserved Instances
  - Evaluate Savings Plans
  - Review overall cloud spend
  - Budget for next year

---

### Emergency Procedures

#### High CPU Alert

1. Check CloudWatch metrics (which instances)
2. Review application logs for errors
3. Check for runaway queries in RDS
4. Manual scale out if needed
5. Investigate root cause

#### Database Connection Exhaustion

1. Check RDS connections metric
2. Identify long-running queries
3. Kill idle connections if needed
4. Review connection pooling settings
5. Consider increasing max_connections

#### 5xx Error Spike

1. Check ALB target health
2. Review application logs
3. Check RDS availability
4. Verify security group rules
5. Roll back recent deployment if needed

---

## Support & References

### AWS Documentation

- **VPC:** https://docs.aws.amazon.com/vpc/
- **RDS:** https://docs.aws.amazon.com/rds/
- **ECS:** https://docs.aws.amazon.com/ecs/
- **CloudFront:** https://docs.aws.amazon.com/cloudfront/
- **Auto Scaling:** https://docs.aws.amazon.com/autoscaling/

### Infrastructure as Code

- **Terraform AWS Provider:** https://registry.terraform.io/providers/hashicorp/aws/
- **AWS CDK:** https://docs.aws.amazon.com/cdk/
- **CloudFormation:** https://docs.aws.amazon.com/cloudformation/

### Monitoring & Observability

- **CloudWatch:** https://docs.aws.amazon.com/cloudwatch/
- **X-Ray:** https://docs.aws.amazon.com/xray/
- **AWS Well-Architected Tool:** https://aws.amazon.com/well-architected-tool/

---

**AWS Architecture Guide Version:** 1.0  
**Last Updated:** January 28, 2026  
**Author:** GitHub Copilot (Claude Sonnet 4.5)

**Related Documentation:**
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete deployment guide
- [README.md](README.md) - Application overview
- [TEST_REPORT.md](TEST_REPORT.md) - Comprehensive test results
