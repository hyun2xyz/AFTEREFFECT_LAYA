import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import laya_route


class LayaRouteTest(unittest.TestCase):
    def test_request_schema(self):
        self.assertEqual(laya_route._validate_requests(["inspect this"]), ["inspect this"])
        for value in ([], [""], ["x" * 401], [1], ["ok"] * 9):
            with self.subTest(value=value), self.assertRaises(ValueError):
                laya_route._validate_requests(value)

    def test_missing_model_and_tokenizer_rejected(self):
        with self.assertRaises(ValueError):
            laya_route._model_path(ROOT / "missing-model")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for name in laya_route.REQUIRED_MODEL_FILES[:-1]:
                target = path / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x")
            with self.assertRaisesRegex(ValueError, "tokenizer"):
                laya_route._model_path(path)

    def test_invalid_probability_labels_and_sum(self):
        raw = {"answers": {"operation": {"type": "choice", "probabilities": {"wrong": 1}, "choice": "inspect", "confidence": 1}, "mode": {"type": "choice", "probabilities": {k: 1/3 for k in laya_route.MODE_LABELS}, "choice": "run", "confidence": 1}}, "usage": {"input_tokens": 2}}
        with self.assertRaisesRegex(ValueError, "probability labels"):
            laya_route._validate_prediction(raw)
        raw["answers"]["operation"] = {"type": "choice", "probabilities": {k: 0.1 for k in laya_route.OPERATION_LABELS}, "choice": "inspect", "confidence": 1}
        with self.assertRaisesRegex(ValueError, "sum"):
            laya_route._validate_prediction(raw)

    def test_valid_prediction(self):
        self.assertIn("set_comp", laya_route.OPERATION_LABELS)
        op = {k: 0.0 for k in laya_route.OPERATION_LABELS}; op["inspect"] = 1.0
        mode = {k: 0.0 for k in laya_route.MODE_LABELS}; mode["explain"] = 1.0
        clean, tokens = laya_route._validate_prediction({"answers": {
            "operation": {"type": "choice", "probabilities": op, "choice": "inspect", "confidence": 1},
            "mode": {"type": "choice", "probabilities": mode, "choice": "explain", "confidence": 1},
        }, "usage": {"input_tokens": 12}})
        self.assertEqual(tokens, 12)
        self.assertEqual(clean["operation"]["choice"], "inspect")
        self.assertIn("concentration", clean["operation"])


if __name__ == "__main__":
    unittest.main()
