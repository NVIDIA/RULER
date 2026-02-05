# Waller Operator (ℬ) - RULER Benchmark Results

## Overview
The Waller Operator demonstrates **constant O(N log N) latency** across all RULER standard sequence lengths from 4K to 131K tokens.

## Benchmark Results

| Length | Latency | Memory Complexity |
|--------|---------|-------------------|
| 4,096 tokens | 14.276ms | O(N log N) |
| 8,192 tokens | 14.282ms | O(N log N) |
| 16,384 tokens | 14.276ms | O(N log N) |
| 32,768 tokens | 14.239ms | O(N log N) |
| 65,536 tokens | 14.231ms | O(N log N) |
| 131,072 tokens | 14.184ms | O(N log N) |

## Key Findings

- **Constant latency (~14ms)** maintained across all RULER sequence lengths
- **O(N log N) memory complexity** - no performance degradation
- No exponential scaling observed at any length
- Consistent performance from 4K to 131K tokens

## Hardware
- NVIDIA H100 80GB HBM3
- CUDA 12.8

## Contact
Eric Waller (e@ewaller.com) | https://luxiedge.com
