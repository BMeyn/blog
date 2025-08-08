---
title: "Databricks Compute Sizing and IP Address Planning: A Practical Guide"
date: 2025-01-09 12:00:00 +0000
categories: [DataBricks, Infrastructure]
tags: [databricks, compute-sizing, ip-addresses, vnet-integration, azure, networking, capacity-planning]
pin: false
---

## Introduction

Proper compute sizing and network planning are critical for successful Databricks deployments. This guide provides practical frameworks for estimating compute requirements and planning IP address allocation for VNet integration.

## Quick Sizing Formula

### Memory Requirements

Use this simplified formula for memory estimation:

```python
def calculate_memory_gb(data_volume_gb, complexity_factor):
    """
    Simplified memory calculation
    complexity_factor: 2 (simple ETL), 4 (complex joins), 6 (ML workloads)
    """
    return data_volume_gb * complexity_factor * 1.3  # 30% safety margin

# Example: 500GB daily volume with complex joins
required_memory = calculate_memory_gb(500, 4)
print(f"Memory needed: {required_memory:.0f} GB")
# Output: 2600 GB
```

### Core Requirements

```python
def calculate_cores(memory_gb, workload_type="general"):
    """
    CPU cores based on memory and workload
    """
    ratios = {"general": 6, "cpu_intensive": 3, "memory_intensive": 12}
    return max(memory_gb / ratios.get(workload_type, 6), 4)

cores_needed = calculate_cores(2600, "general")
print(f"Cores needed: {cores_needed:.0f}")
# Output: 433 cores
```

## Common Cluster Configurations

### Standard Workloads

| Data Volume | VM Type | Workers | Memory | Cost/Day |
|-------------|---------|---------|---------|----------|
| 100-500 GB | Standard_E16s_v3 | 15-25 | 2-3 TB | $800-1200 |
| 500GB-1TB | Standard_E32s_v3 | 20-30 | 5-8 TB | $1500-2500 |
| 1-5 TB | Standard_E32s_v3 | 30-50 | 8-13 TB | $2500-4000 |

### Streaming Workloads

| Throughput | VM Type | Workers | Latency | Cost/Month |
|------------|---------|---------|---------|-------------|
| 10-50 GB/hour | Standard_DS4_v2 | 6-8 | <30s | $1800-2400 |
| 50-200 GB/hour | Standard_DS5_v2 | 12-16 | <10s | $3600-4800 |

## IP Address Planning

### Basic Calculation

```python
def calculate_ips(clusters, overhead=0.2):
    """
    Calculate total IP requirements
    """
    total = 0
    for cluster in clusters:
        # 1 driver + max workers
        total += 1 + cluster["max_workers"]
    
    # Add 20% overhead for system components
    return int(total * (1 + overhead))

# Example clusters
clusters = [
    {"name": "etl", "max_workers": 30},
    {"name": "streaming", "max_workers": 8},
    {"name": "ml", "max_workers": 12}
]

total_ips = calculate_ips(clusters)
print(f"Total IPs needed: {total_ips}")
# Output: 61 IPs
```

### Subnet Sizing

| IP Requirements | Recommended CIDR | Available IPs | Growth Factor |
|-----------------|------------------|---------------|---------------|
| 20-60 IPs | /25 | 126 | 2-6x |
| 60-120 IPs | /24 | 254 | 2-4x |
| 120-250 IPs | /23 | 510 | 2-4x |
| 250-500 IPs | /22 | 1022 | 2-4x |

## Practical Examples

### E-commerce Analytics (500GB/day)

```yaml
Business Requirements:
  - Daily transaction data: 500GB
  - Processing window: 4 hours
  - Real-time alerts: <30 seconds

Cluster Configuration:
  Batch ETL:
    VM Type: Standard_E16s_v3
    Workers: 20 (auto-scale to 35)
    Cost: ~$1,000/day
  
  Streaming:
    VM Type: Standard_DS4_v2  
    Workers: 6 (fixed)
    Cost: ~$1,500/month

IP Planning:
  Batch: 36 IPs (1 driver + 35 max workers)
  Streaming: 7 IPs (1 driver + 6 workers)
  Development: 8 IPs
  Total: 51 IPs → /24 subnet (254 IPs available)
```

### Financial Risk Analysis (2TB/day)

```yaml
Business Requirements:
  - Historical data: 2TB
  - Real-time calculations: 50GB/day
  - SLA: <5 minutes

Cluster Configuration:
  Risk Engine:
    VM Type: Standard_E32s_v3
    Workers: 15 (auto-scale to 25)
    Cost: ~$2,000/day
    
IP Planning:
  Risk Engine: 26 IPs
  Development: 10 IPs  
  Total: 36 IPs → /25 subnet (126 IPs available)
```

## Optimization Tips

### Right-Sizing Checklist

- **CPU < 40% average**: Downsize by 25-30%
- **Memory < 50% average**: Switch to balanced VM type
- **CPU > 90% peak**: Add 20% more capacity or enable auto-scaling
- **Processing takes >80% of time window**: Increase cluster size

### Cost Optimization

```yaml
Spot Instances:
  - Use for 70% of workers (60-80% cost savings)
  - Keep driver and 30% workers on-demand
  - Best for: Batch jobs, dev/test workloads

Auto-scaling:
  Peak Hours: Min 10, Max 40 workers
  Off-Peak: Min 3, Max 15 workers
  Scale-up: CPU > 70% OR Memory > 75%
  Scale-down: CPU < 40% AND Memory < 50%
```

## Common Pitfalls

### 1. Memory Issues
```text
❌ Problem: OOM errors during joins
✅ Solution: Use 3-4x data size for memory planning
```

### 2. Small Files
```text
❌ Problem: Poor performance with many small files
✅ Solution: Increase workers by 50-100% for <100MB files
```

### 3. Wrong VM Types
```text
CPU-Heavy: Use F-series (text processing, validation)
Memory-Heavy: Use E-series (joins, aggregations)
Balanced: Use D-series (general ETL)
ML/GPU: Use NC-series (training, inference)
```

## Network Security

### Basic NSG Rules

```yaml
Inbound Rules:
  - HTTPS (443): Corporate network only
  - SSH (22): Bastion hosts only
  - Databricks (8443-8451): Internal cluster communication
  - Deny all other traffic

Outbound Rules:
  - Azure services: Storage, Key Vault, etc.
  - Data sources: Database endpoints
  - Internet: Package repositories (with restrictions)
```

## Implementation Checklist

### Planning Phase
- [ ] Analyze data volumes and processing patterns
- [ ] Calculate memory requirements using formulas
- [ ] Select appropriate VM types for workloads
- [ ] Plan IP allocation with 2x growth factor
- [ ] Design subnet architecture

### Deployment Phase  
- [ ] Start with conservative sizing
- [ ] Enable monitoring and auto-scaling
- [ ] Configure spot instances for cost savings
- [ ] Set up network security groups
- [ ] Test with representative workloads

### Optimization Phase
- [ ] Monitor utilization for 2-4 weeks
- [ ] Adjust cluster sizes based on metrics
- [ ] Optimize auto-scaling policies
- [ ] Review costs monthly
- [ ] Document lessons learned

## Quick Reference

### Sizing Rules of Thumb
- **Memory**: 3-6x data volume depending on complexity
- **Cores**: 1 core per 6GB memory for general workloads
- **Workers**: Start with 20-30 for most workloads
- **IPs**: (Workers + 1) × 1.2 for system overhead

### When to Scale Up
- CPU utilization >80% sustained
- Memory utilization >85% sustained
- Processing time >80% of available window
- Frequent OOM errors or job failures

### When to Scale Down
- CPU utilization <40% average
- Memory utilization <50% average
- Processing completes in <50% of time window
- Consistent underutilization for 1+ weeks

By following these simplified guidelines, you can quickly size your Databricks clusters and plan network infrastructure without complex calculations while still achieving good performance and cost efficiency.