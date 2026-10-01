"""Regression tests for revised performance-vs-correctness qualification semantics."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import evaluate_campaign_v2 as mod


class Gates(unittest.TestCase):
    def evaluate(self, *, candidate_decode=110, gap=0, cache_mismatch=False):
        roles=('base_overlap','candidate_overlap','base_decode','candidate_decode')
        pairs=[{role:f'{i}-{role}' for role in roles} for i in range(5)]
        def load(name,root):
            role=name.split('-',1)[1]
            return ({'role':role,'environment':{},'strict':False,'sha256':'frozen' if role.startswith('base') else 'candidate',
                     'args':[],'workload':[]},
                    {'path':name,'source_sha256':name,'actual_cache_slots':100 if not cache_mismatch or role.startswith('base') else 99})
        def overlap(report):
            candidate=report['role'].startswith('candidate')
            return [dict(D=40 if candidate else 10,P=800 if candidate else 1000,U=32000 if candidate else 10000,
                         incoming_ttft_s=12 if candidate else 10,workflow_s=30,
                         long_gap_request_seconds=gap if candidate else 10)]
        with patch.object(mod,'load_report',load),patch.object(mod,'sha',return_value='frozen'),\
             patch.object(mod,'parity',return_value={'equal':False}),patch.object(mod,'overlap_metrics',overlap),\
             patch.object(mod,'decode_metrics',lambda r:{'TPS':candidate_decode if r['role'].startswith('candidate') else 100}):
            return mod.evaluate(pairs)

    def test_normal_token_difference_does_not_veto_performance(self):
        result=self.evaluate()
        self.assertTrue(result['performance_pass'])
        self.assertFalse(result['pairs'][0]['normal_token_parity_diagnostic']['decode']['equal'])
        self.assertIn('correctness',result['limitation'])

    def test_decode_regression_and_gap_threshold_still_block(self):
        self.assertFalse(self.evaluate(candidate_decode=96.9)['performance_pass'])
        self.assertFalse(self.evaluate(gap=5.01)['performance_pass'])
        self.assertTrue(self.evaluate(candidate_decode=97,gap=5)['performance_pass'])

    def test_unequal_residency_rejected(self):
        with self.assertRaises(AssertionError): self.evaluate(cache_mismatch=True)


if __name__=='__main__': unittest.main()
