"""
AWS On-Demand pricing (us-east-1) and downsize maps for rightsizing recommendations.
All compute prices in USD/hour unless noted.
"""

HOURS_MONTH = 730

# =====================================================
# EC2 INSTANCE PRICING (us-east-1, Linux, On-Demand)
# =====================================================
EC2_PRICING: dict = {
    "t3.nano": 0.0052,  "t3.micro": 0.0104, "t3.small": 0.0208,
    "t3.medium": 0.0416, "t3.large": 0.0832, "t3.xlarge": 0.1664, "t3.2xlarge": 0.3328,
    "t3a.nano": 0.0047,  "t3a.micro": 0.0094, "t3a.small": 0.0188,
    "t3a.medium": 0.0376, "t3a.large": 0.0752, "t3a.xlarge": 0.1504, "t3a.2xlarge": 0.3008,
    "m5.large": 0.096,   "m5.xlarge": 0.192,  "m5.2xlarge": 0.384,
    "m5.4xlarge": 0.768, "m5.8xlarge": 1.536, "m5.12xlarge": 2.304,
    "m6i.large": 0.096,  "m6i.xlarge": 0.192, "m6i.2xlarge": 0.384,
    "m6i.4xlarge": 0.768, "m6i.8xlarge": 1.536,
    "m7i.large": 0.1008, "m7i.xlarge": 0.2016, "m7i.2xlarge": 0.4032, "m7i.4xlarge": 0.8064,
    "c5.large": 0.085,   "c5.xlarge": 0.170,  "c5.2xlarge": 0.340,
    "c5.4xlarge": 0.680, "c5.9xlarge": 1.530,
    "c6i.large": 0.085,  "c6i.xlarge": 0.170, "c6i.2xlarge": 0.340,
    "c6i.4xlarge": 0.680, "c6i.8xlarge": 1.360,
    "c7i.large": 0.08925, "c7i.xlarge": 0.17850, "c7i.2xlarge": 0.35700, "c7i.4xlarge": 0.71400,
    "r5.large": 0.126,  "r5.xlarge": 0.252,  "r5.2xlarge": 0.504,
    "r5.4xlarge": 1.008, "r5.8xlarge": 2.016,
    "r6i.large": 0.126,  "r6i.xlarge": 0.252, "r6i.2xlarge": 0.504,
    "r6i.4xlarge": 1.008, "r6i.8xlarge": 2.016,
    "r7i.large": 0.1323, "r7i.xlarge": 0.2646, "r7i.2xlarge": 0.5292, "r7i.4xlarge": 1.0584,
}

# One step down within the same instance family
EC2_DOWNSIZE: dict = {
    "t3.2xlarge": "t3.xlarge",  "t3.xlarge": "t3.large",   "t3.large": "t3.medium",
    "t3.medium": "t3.small",    "t3.small": "t3.micro",
    "t3a.2xlarge": "t3a.xlarge", "t3a.xlarge": "t3a.large", "t3a.large": "t3a.medium",
    "t3a.medium": "t3a.small",  "t3a.small": "t3a.micro",
    "m5.12xlarge": "m5.8xlarge", "m5.8xlarge": "m5.4xlarge", "m5.4xlarge": "m5.2xlarge",
    "m5.2xlarge": "m5.xlarge",  "m5.xlarge": "m5.large",
    "m6i.8xlarge": "m6i.4xlarge", "m6i.4xlarge": "m6i.2xlarge",
    "m6i.2xlarge": "m6i.xlarge", "m6i.xlarge": "m6i.large",
    "m7i.4xlarge": "m7i.2xlarge", "m7i.2xlarge": "m7i.xlarge", "m7i.xlarge": "m7i.large",
    "c5.9xlarge": "c5.4xlarge",  "c5.4xlarge": "c5.2xlarge",
    "c5.2xlarge": "c5.xlarge",   "c5.xlarge": "c5.large",
    "c6i.8xlarge": "c6i.4xlarge", "c6i.4xlarge": "c6i.2xlarge",
    "c6i.2xlarge": "c6i.xlarge",  "c6i.xlarge": "c6i.large",
    "c7i.4xlarge": "c7i.2xlarge", "c7i.2xlarge": "c7i.xlarge", "c7i.xlarge": "c7i.large",
    "r5.8xlarge": "r5.4xlarge",  "r5.4xlarge": "r5.2xlarge",
    "r5.2xlarge": "r5.xlarge",   "r5.xlarge": "r5.large",
    "r6i.8xlarge": "r6i.4xlarge", "r6i.4xlarge": "r6i.2xlarge",
    "r6i.2xlarge": "r6i.xlarge",  "r6i.xlarge": "r6i.large",
    "r7i.4xlarge": "r7i.2xlarge", "r7i.2xlarge": "r7i.xlarge", "r7i.xlarge": "r7i.large",
}

# =====================================================
# RDS PRICING (us-east-1, MySQL/PostgreSQL, Single-AZ)
# =====================================================
RDS_PRICING: dict = {
    "db.t3.micro": 0.017,   "db.t3.small": 0.034,   "db.t3.medium": 0.068,
    "db.t3.large": 0.136,   "db.t3.xlarge": 0.272,  "db.t3.2xlarge": 0.544,
    "db.m5.large": 0.171,   "db.m5.xlarge": 0.342,  "db.m5.2xlarge": 0.684,
    "db.m5.4xlarge": 1.368, "db.m5.8xlarge": 2.736,
    "db.m6g.large": 0.153,  "db.m6g.xlarge": 0.306,
    "db.m6g.2xlarge": 0.612, "db.m6g.4xlarge": 1.224,
    "db.m7g.large": 0.153,  "db.m7g.xlarge": 0.306,  "db.m7g.2xlarge": 0.612,
    "db.r5.large": 0.240,   "db.r5.xlarge": 0.480,  "db.r5.2xlarge": 0.960,  "db.r5.4xlarge": 1.920,
    "db.r6g.large": 0.240,  "db.r6g.xlarge": 0.480, "db.r6g.2xlarge": 0.960,
    "db.r7g.large": 0.240,  "db.r7g.xlarge": 0.480, "db.r7g.2xlarge": 0.960,
}

RDS_DOWNSIZE: dict = {
    "db.t3.2xlarge": "db.t3.xlarge",  "db.t3.xlarge": "db.t3.large",
    "db.t3.large": "db.t3.medium",    "db.t3.medium": "db.t3.small",
    "db.t3.small": "db.t3.micro",
    "db.m5.8xlarge": "db.m5.4xlarge", "db.m5.4xlarge": "db.m5.2xlarge",
    "db.m5.2xlarge": "db.m5.xlarge",  "db.m5.xlarge": "db.m5.large",
    "db.m6g.4xlarge": "db.m6g.2xlarge", "db.m6g.2xlarge": "db.m6g.xlarge",
    "db.m6g.xlarge": "db.m6g.large",
    "db.m7g.2xlarge": "db.m7g.xlarge", "db.m7g.xlarge": "db.m7g.large",
    "db.r5.4xlarge": "db.r5.2xlarge",  "db.r5.2xlarge": "db.r5.xlarge",
    "db.r5.xlarge": "db.r5.large",
    "db.r6g.2xlarge": "db.r6g.xlarge", "db.r6g.xlarge": "db.r6g.large",
    "db.r7g.2xlarge": "db.r7g.xlarge", "db.r7g.xlarge": "db.r7g.large",
}

# =====================================================
# REDSHIFT NODE PRICING (us-east-1, On-Demand)
# =====================================================
REDSHIFT_PRICING: dict = {
    "dc2.large": 0.25,    "dc2.8xlarge": 4.80,
    "ds2.xlarge": 0.85,   "ds2.8xlarge": 6.80,
    "ra3.xlplus": 1.086,  "ra3.4xlarge": 3.26, "ra3.16xlarge": 13.04,
}

REDSHIFT_DOWNSIZE: dict = {
    "ra3.16xlarge": "ra3.4xlarge",
    "ra3.4xlarge":  "ra3.xlplus",
    "dc2.8xlarge":  "dc2.large",
    "ds2.8xlarge":  "ds2.xlarge",
}

# =====================================================
# ECS FARGATE PRICING (us-east-1, Linux/x86)
# =====================================================
ECS_VCPU_HR    = 0.04048   # per vCPU-hour
ECS_MEM_GB_HR  = 0.004445  # per GB-hour

# Downsize map: current CPU units -> recommended CPU units
ECS_CPU_DOWNSIZE: dict = {4096: 2048, 2048: 1024, 1024: 512, 512: 256}

# Minimum valid memory (MB) per CPU step
ECS_MIN_MEMORY: dict = {256: 512, 512: 1024, 1024: 2048, 2048: 4096, 4096: 8192}

# =====================================================
# LAMBDA PRICING
# =====================================================
LAMBDA_MEMORY_STEPS = [
    128, 256, 512, 1024, 1536, 2048, 3008,
    4096, 5120, 6144, 7168, 8192, 9216, 10240,
]
LAMBDA_GB_SEC = 0.0000166667

# =====================================================
# DYNAMODB PRICING (us-east-1, provisioned capacity)
# =====================================================
DYNAMO_WCU_MONTH = 0.00065   # per provisioned WCU per month
DYNAMO_RCU_MONTH = 0.00013   # per provisioned RCU per month

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def ec2_monthly(instance_type: str) -> float:
    return EC2_PRICING.get(instance_type, 0.0) * HOURS_MONTH


def rds_monthly(instance_class: str, multi_az: bool = False) -> float:
    price = RDS_PRICING.get(instance_class, 0.0) * HOURS_MONTH
    return price * 2 if multi_az else price


def ecs_task_monthly(cpu_units: int, memory_mb: int, tasks: int) -> float:
    vcpu   = cpu_units / 1024
    mem_gb = memory_mb / 1024
    return (vcpu * ECS_VCPU_HR + mem_gb * ECS_MEM_GB_HR) * tasks * HOURS_MONTH


def lambda_monthly_cost(memory_mb: int, monthly_invocations: int, avg_duration_ms: float) -> float:
    gb_sec = (memory_mb / 1024) * (avg_duration_ms / 1000) * monthly_invocations
    return gb_sec * LAMBDA_GB_SEC


def next_smaller_lambda_memory(current_mb: int):
    valid = [m for m in LAMBDA_MEMORY_STEPS if m < current_mb]
    return max(valid) if valid else None
