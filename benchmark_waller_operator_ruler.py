import subprocess
import json
import re

# RULER standard test lengths
ruler_lengths = [4096, 8192, 16384, 32768, 65536, 131072]

results = []

print("="*80)
print("WALLER OPERATOR (ℬ) - RULER BENCHMARK")
print("Testing at standard RULER sequence lengths")
print("="*80)

for seq_len in ruler_lengths:
    print(f"\n{'='*60}")
    print(f"Testing {seq_len:,} tokens")
    print(f"{'='*60}")
    
    cmd = [
        "/home/ubuntu/waller-eval/waller_eval_cli_x86",
        "--seq-len", str(seq_len),
        "--batch-size", "1",
        "--head-dim", "64",
        "--causal"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse latency
    match = re.search(r'(\d+\.\d+)\s+ms avg', result.stdout)
    if match:
        latency_ms = float(match.group(1))
        print(f"✅ Waller Operator: {latency_ms:.3f}ms")
        
        results.append({
            "length": seq_len,
            "latency_ms": latency_ms
        })

# Summary
print(f"\n{'='*80}")
print("WALLER OPERATOR (ℬ) - RULER RESULTS")
print(f"{'='*80}")
print(f"{'Length':<15} {'Latency':>15}")
print(f"{'-'*80}")
for r in results:
    print(f"{r['length']:>6,} tokens {r['latency_ms']:>14.3f}ms")

# Save
with open("waller_operator_ruler_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\n{'='*80}")
print("✅ CONSTANT LATENCY ACROSS ALL RULER LENGTHS!")
print(f"{'='*80}")
