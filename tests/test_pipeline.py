import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from emoemg.pipeline import Config, Predictor, features, load_csv, replay, simulate, train


class PipelineTests(unittest.TestCase):
    def test_end_to_end_and_split_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = Config()
            simulate(root/"data", cfg)
            paths = sorted((root/"data").glob("*.csv"))
            artifact, report = train(paths[:3], paths[3:], cfg, root/"run")
            self.assertEqual(report["test_sessions"], ["session-3.csv"])
            self.assertGreater(report["metrics"]["accuracy"], .8)  # synthetic smoke only
            p = Predictor(artifact)
            _, x, _ = load_csv(paths[3], cfg)
            self.assertIn(p.predict(x[:cfg.n])[0], artifact["classes"])
            replay(root/"run/model.json", paths[3], root/"predictions.csv")
            self.assertGreater(len((root/"predictions.csv").read_text().splitlines()), 10)
            with self.assertRaises(ValueError):
                train(paths[:3], paths[2:], cfg, root/"bad")
            (root/"duplicate.csv").write_bytes(paths[0].read_bytes())
            with self.assertRaises(ValueError):
                train(paths[:3], [root/"duplicate.csv"], cfg, root/"bad")
            with self.assertRaises(FileExistsError):
                train(paths[:3], paths[3:], cfg, root/"run")

    def test_binary_probability_and_invalid_signals(self):
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        rng = np.random.default_rng(4)
        cfg = Config()
        windows = [rng.normal(size=(cfg.n,4)) for _ in range(12)]
        x = np.array([features(w,cfg) for w in windows])
        scaler = StandardScaler().fit(x)
        model = LogisticRegression().fit(scaler.transform(x), ["a","b"]*6)
        from dataclasses import asdict
        artifact = dict(schema_version=1, feature_version=1, config=asdict(cfg),
                        channels=["ch1","ch2","ch3","ch4"], classes=model.classes_.tolist(),
                        mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist(),
                        coef=model.coef_.tolist(), intercept=model.intercept_.tolist())
        predictor = Predictor(artifact)
        for w, probs in zip(windows, model.predict_proba(scaler.transform(x))):
            label, score = predictor.predict(w)
            self.assertEqual(label, model.classes_[probs.argmax()])
            self.assertAlmostEqual(score, probs.max())
        with self.assertRaises(ValueError):
            features(np.zeros((cfg.n,4)),cfg)
        with self.assertRaises(ValueError):
            Config(sample_rate=50).validate()
        with self.assertRaises(ValueError):
            features(np.full((cfg.n,4), np.nan),cfg)

    def test_timestamp_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"bad.csv"
            path.write_text("timestamp,ch1,ch2,ch3,ch4,label\n" +
                            "\n".join(f"{i},1,2,3,4,rest" for i in range(250)))
            with self.assertRaises(ValueError):
                load_csv(path, Config())


if __name__ == "__main__":
    unittest.main()
