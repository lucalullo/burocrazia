"""Rerun unchanged historical/canonical contracts into separate Round 9 outputs."""
import argparse
from benchmarks import round8_common as common,round8_validation as previous
from benchmarks.transactional_writer import atomic_json
OUT='benchmarks/results/round9/'

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['historical','canonical','family']);a=p.parse_args()
    common.OUT=OUT;common.SEED=2026101209;previous.OUT=OUT
    def write(path,value):return atomic_json(common.ROOT/path,value)
    common.write=write;previous.write=write
    getattr(previous,a.mode)()
if __name__=='__main__':main()
