import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[2] / "tools/configure_concurrency_candidate.py"
spec = importlib.util.spec_from_file_location("candidate_config", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CandidateConfigTests(unittest.TestCase):
    def source(self, gpu):
        return {"gpu": gpu, "model_name": "test", "args": [
            "--pack", "pack", "--native", "model.gguf", "--expert-profile", "profile.bin", "--mtp", "mtp"]}

    def test_multi_gpu_preserves_order_and_enables_layer_split(self):
        source = self.source([1, 0])
        result = mod.configure(source, Path("strata"), 32768, 2560, "auto")
        self.assertEqual(result["gpu"], [1, 0])
        self.assertEqual(result["layer_split"], "auto")
        self.assertEqual(source, self.source([1, 0]))
        args = dict(zip(result["args"][::2], result["args"][1::2]))
        self.assertEqual(args["--concurrency"], "4")

    def test_large_context_is_per_request(self):
        result = mod.configure(self.source([0, 1]), Path("strata"), 131072, 2560, "auto")
        args = dict(zip(result["args"][::2], result["args"][1::2]))
        self.assertEqual(args["--max-context"], "131072")
        self.assertEqual(args["--concurrency"], "4")
        self.assertEqual(args["--kv"], "int8")

    def test_single_gpu_remains_single(self):
        result = mod.configure(self.source(1), Path("strata"), 32768, 2560, "auto")
        self.assertEqual(result["gpu"], 1)
        self.assertNotIn("layer_split", result)

    def test_invalid_gpu_sets_are_rejected(self):
        for gpu in ([0, 0], [0], [-1, 0], ["0", 1], [True, 1], list(range(9))):
            with self.subTest(gpu=gpu), self.assertRaises(ValueError):
                mod.configure(self.source(gpu), Path("strata"), 32768, 2560, "auto")

    def test_unsupported_modalities_and_streamed_kv_stay_rejected(self):
        for extra in ({"vision": {"exe": "vision"}}, {"backend": "hip"}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                mod.configure(dict(self.source([0, 1]), **extra), Path("strata"), 32768, 2560, "auto")
        source = self.source([0, 1])
        source["args"] += ["--kv-resident", "32768"]
        with self.assertRaises(ValueError):
            mod.configure(source, Path("strata"), 32768, 2560, "auto")


if __name__ == "__main__":
    unittest.main()
