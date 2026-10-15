"""Seven new required post-V6 warm runs, unchanged67-input paired protocol."""
from scripts.round22_common import *
from benchmarks.round22_release import sealed
from benchmarks import round21_performance as protocol

def main():
    sealed();assert (OUT/'evaluation_v6_gate.json').exists();assert (OUT/'post_v6_checks.json').exists()
    protocol.OUT=OUT/'performance_stability.json'
    checkpoint('Round22 post-V6 seven-run isolated performance','Frozen engine/generator/V6 unchanged. Canonical/safety and full tests completed before isolated timings.', 'Run all7 predefined warm runs once;no optimization/rerun after V6. Follow reports/round22-performance.log.',[dict(command='python -m benchmarks.round22_performance',log='reports/round22-performance.log',state='running in isolation')])
    protocol.main();sealed()

if __name__=='__main__':main()
