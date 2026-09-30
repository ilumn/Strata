import importlib.util
from pathlib import Path
import tempfile
import struct
import unittest
import numpy as np
spec=importlib.util.spec_from_file_location('numerical_compare',Path(__file__).resolve().parents[2]/'tools/numerical_compare.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

class NumericalTests(unittest.TestCase):
    def test_shift_invariant(self):
        a=np.array([1.,2.,4.]); result=mod.metrics(a,a+100)
        self.assertLess(result['kl'],1e-12); self.assertLess(result['tv'],1e-12)
    def test_detects_wrong_distribution(self):
        result=mod.metrics(np.array([10.,0.,-1.]),np.array([0.,10.,-1.]))
        self.assertGreater(result['kl'],9); self.assertGreater(result['tv'],.99)
    def test_small_tie_can_flip_without_large_error(self):
        result=mod.metrics(np.array([1.,1.00001,0.]),np.array([1.00001,1.,0.]))
        self.assertFalse(result['top1_equal']); self.assertLess(result['kl'],1e-9)
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError): mod.metrics(np.array([1.,float('nan')]),np.array([1.,2.]))
    def test_truncated_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'x'; path.write_bytes(struct.pack('<QQQQ',100,0,50,3)+b'1234')
            with self.assertRaises(ValueError): mod.read(path)
    def test_context_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[Path(directory)/name for name in ('a','b')]
            for i,path in enumerate(paths): path.write_bytes(struct.pack('<QQQQ',100,0,50+i,3)+np.array([1,2,3],dtype='<f4').tobytes())
            with self.assertRaises(ValueError): mod.compare(*paths)

if __name__=='__main__': unittest.main()
