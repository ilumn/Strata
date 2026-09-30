import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "compare_round_traces", Path(__file__).resolve().parents[2] / "tools/compare_round_traces.py")
traces = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(traces)


class RoundTraceTests(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.log"
            path.write_text(text, encoding="utf-8")
            return traces.read_trace(path)

    def test_first_proposal_change_precedes_common_output_change(self):
        left = self.read("round-input 7 id=100 pos=10 count=2 lookup=0 tokens=1,2\n"
                         "round-output 7 id=100 tokens=2,3\n"
                         "round-output 9 id=100 tokens=4,5\n")
        right = self.read("round-input 7 id=100 pos=10 count=3 lookup=1 tokens=1,2,8\n"
                          "round-output 7 id=100 tokens=2,3,9\n"
                          "round-output 9 id=100 tokens=4,6\n")
        result = traces.compare(left, right)
        self.assertEqual(result["input"]["round"], 7)
        self.assertEqual(result["output"]["round"], 7)
        self.assertEqual(result["common_output_token"]["round"], 9)
        self.assertEqual(result["common_output_token"]["row"], 1)

    def test_missing_record_is_not_silently_equal(self):
        left = self.read("round-order 0 100:4\n")
        result = traces.compare(left, {})
        self.assertEqual(result["order"]["left"], "100:4")
        self.assertIsNone(result["order"]["right"])

    def test_duplicate_process_rounds_rejected(self):
        with self.assertRaises(ValueError):
            self.read("round-order 0 100:4\nround-order 0 100:4\n")

    def test_empty_trace_rejected(self):
        with self.assertRaises(ValueError):
            self.read("no tracing enabled\n")


if __name__ == "__main__":
    unittest.main()
