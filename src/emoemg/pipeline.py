"""FACET offline baseline. CSV replay only; no hardware or emotion inference."""
from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path
import numpy as np
from scipy import signal
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CHANNELS = ("ch1", "ch2", "ch3", "ch4")


@dataclass(frozen=True)
class Config:
    sample_rate: float = 250.0
    window_seconds: float = 1.0
    hop_seconds: float = 0.25
    low_hz: float = 1.0
    high_hz: float = 45.0
    notch_hz: float = 0.0

    def validate(self):
        values = list(asdict(self).values())
        if not np.isfinite(values).all():
            raise ValueError("Config must be finite")
        if not 0 < self.low_hz < self.high_hz < self.sample_rate / 2:
            raise ValueError("Require 0 < low < high < Nyquist")
        if not 0 < self.hop_seconds <= self.window_seconds:
            raise ValueError("Require 0 < hop <= window")
        if self.n < 16 or self.hop < 1:
            raise ValueError("Window too short or hop below one sample")
        if self.notch_hz and not 0 < self.notch_hz < self.sample_rate / 2:
            raise ValueError("Notch must be zero (disabled) or below Nyquist")
        return self

    @property
    def n(self):
        return round(self.sample_rate * self.window_seconds)

    @property
    def hop(self):
        return round(self.sample_rate * self.hop_seconds)


def load_csv(path, config, labeled=True):
    """One continuous session/file; timestamps seconds, four channels same units."""
    config.validate()
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", *CHANNELS} | ({"label"} if labeled else set())
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"{path}: required columns: {sorted(required)}")
        rows = list(reader)
    if len(rows) < config.n:
        raise ValueError(f"{path}: fewer samples than one window")
    t = np.array([float(r["timestamp"]) for r in rows])
    x = np.array([[float(r[c]) for c in CHANNELS] for r in rows])
    if not np.isfinite(x).all() or not np.isfinite(t).all():
        raise ValueError("Nonfinite samples or timestamps")
    if not np.allclose(np.diff(t), 1 / config.sample_rate, rtol=0.05, atol=1e-6):
        raise ValueError("Timestamp gaps or sample rate mismatch; resample explicitly")
    labels = np.array([r["label"].strip() for r in rows]) if labeled else None
    if labeled and np.any(labels == ""):
        raise ValueError("Empty action label")
    return t, x, labels


def features(window, config):
    """Identical window-local causal filtering in train and replay; resets per window."""
    config.validate()
    x = np.asarray(window, dtype=float)
    if x.shape != (config.n, 4) or not np.isfinite(x).all():
        raise ValueError("Expected one finite [window_samples, 4] window")
    if np.any(np.ptp(x, axis=0) < 1e-12):
        raise ValueError("Flat channel; rejected by signal quality gate")
    x = x - x.mean(axis=0)
    if config.notch_hz:
        b, a = signal.iirnotch(config.notch_hz, 30, fs=config.sample_rate)
        x = signal.lfilter(b, a, x, axis=0)
    sos = signal.butter(4, [config.low_hz, config.high_hz],
                        fs=config.sample_rate, btype="bandpass", output="sos")
    x = signal.sosfilt(sos, x, axis=0)
    rms = np.sqrt(np.mean(x*x, axis=0))
    mav = np.mean(np.abs(x), axis=0)
    waveform = np.mean(np.abs(np.diff(x, axis=0)), axis=0)
    crossings = np.mean(x[:-1]*x[1:] < 0, axis=0)
    f, psd = signal.welch(x, fs=config.sample_rate, axis=0,
                          nperseg=min(128, config.n))
    bands = []
    for low, high in ((1, 8), (8, 15), (15, 30), (30, 45)):
        mask = (f >= low) & (f < high)
        bands.append(np.log1p(np.sum(psd[mask], axis=0) * (f[1]-f[0])))
    return np.concatenate([rms, mav, waveform, crossings, *bands])


def dataset(paths, config):
    xs, ys, groups = [], [], []
    skipped_transition = skipped_quality = 0
    for path in paths:
        _, raw, labels = load_csv(path, config)
        for start in range(0, len(raw)-config.n+1, config.hop):
            labels_window = labels[start:start+config.n]
            if np.any(labels_window != labels_window[0]):
                skipped_transition += 1
                continue
            try:
                feat = features(raw[start:start+config.n], config)
            except ValueError:
                skipped_quality += 1
                continue
            xs.append(feat)
            ys.append(labels_window[0])
            groups.append(str(Path(path).resolve()))
    if not xs:
        raise ValueError("No valid labeled windows")
    return np.asarray(xs), np.asarray(ys), np.asarray(groups), {
        "transition_windows_skipped": skipped_transition,
        "quality_windows_skipped": skipped_quality,
    }


def train(train_paths, test_paths, config, output):
    """Explicit session-disjoint split; test labels never used for model fitting."""
    config.validate()
    train_set = {Path(p).resolve() for p in train_paths}
    test_set = {Path(p).resolve() for p in test_paths}
    if not train_set or not test_set or train_set & test_set:
        raise ValueError("Provide nonempty, disjoint train and test session files")
    # Catch copied recordings even under different names.
    import hashlib
    hashes = lambda paths: {hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if hashes(train_set) & hashes(test_set):
        raise ValueError("Duplicate recording across train/test")
    x, y, _, train_stats = dataset(sorted(train_set), config)
    xt, yt, _, test_stats = dataset(sorted(test_set), config)
    if len(np.unique(y)) < 2:
        raise ValueError("Training requires at least two action classes")
    if set(yt) - set(y):
        raise ValueError("Test contains labels absent from training")
    model = make_pipeline(StandardScaler(), LogisticRegression(
        class_weight="balanced", max_iter=2000, random_state=42))
    model.fit(x, y)
    predicted = model.predict(xt)
    scaler, classifier = model.steps[0][1], model.steps[1][1]
    artifact = {
        "schema_version": 1, "feature_version": 1, "config": asdict(config),
        "channels": list(CHANNELS), "classes": classifier.classes_.tolist(),
        "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(),
        "coef": classifier.coef_.tolist(), "intercept": classifier.intercept_.tolist(),
    }
    report = {
        "train_sessions": [p.name for p in sorted(train_set)],
        "test_sessions": [p.name for p in sorted(test_set)],
        "train_windows": len(y), "test_windows": len(yt),
        "train_quality": train_stats, "test_quality": test_stats,
        "classes": artifact["classes"],
        "metrics": classification_report(yt, predicted, labels=classifier.classes_,
                                          output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(yt, predicted, labels=classifier.classes_).tolist(),
        "missing_test_classes": sorted(set(y)-set(yt)),
        "note": "Session holdout, not subject-independent unless sessions use distinct subjects. Synthetic inputs provide software validation only.",
    }
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=False)
    (dest/"model.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    (dest/"report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return artifact, report


class Predictor:
    """Portable JSON linear model; no pickle deserialization."""
    def __init__(self, artifact):
        if artifact["schema_version"] != 1 or artifact["feature_version"] != 1:
            raise ValueError("Unsupported model/feature version")
        if artifact["channels"] != list(CHANNELS):
            raise ValueError("Channel order mismatch")
        self.config = Config(**artifact["config"]).validate()
        self.classes = artifact["classes"]
        self.mean = np.asarray(artifact["mean"])
        self.scale = np.asarray(artifact["scale"])
        self.coef = np.asarray(artifact["coef"])
        self.intercept = np.asarray(artifact["intercept"])
        k = len(self.classes)
        rows = 1 if k == 2 else k
        if k < 2 or len(set(self.classes)) != k or self.mean.shape != (32,) or self.scale.shape != (32,) or self.coef.shape != (rows,32) or self.intercept.shape != (rows,):
            raise ValueError("Invalid model dimensions/classes")
        if not all(np.isfinite(a).all() for a in (self.mean,self.scale,self.coef,self.intercept)) or np.any(self.scale <= 0):
            raise ValueError("Invalid model parameters")

    def predict(self, window):
        z = (features(window, self.config)-self.mean)/self.scale
        scores = self.coef @ z + self.intercept
        if len(self.classes) == 2:
            p = 1 / (1 + np.exp(-np.clip(scores[0], -700, 700)))
            probs = np.array([1-p, p])
        else:
            probs = np.exp(scores - scores.max())
            probs /= probs.sum()
        best = int(probs.argmax())
        return self.classes[best], float(probs[best])


def replay(model_path, csv_path, output):
    predictor = Predictor(json.loads(Path(model_path).read_text(encoding="utf-8")))
    t, x, _ = load_csv(csv_path, predictor.config, labeled=False)
    with Path(output).open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "label", "score", "quality"])
        for start in range(0, len(x)-predictor.config.n+1, predictor.config.hop):
            end = start + predictor.config.n
            try:
                label, score = predictor.predict(x[start:end])
                quality = "ok"
            except ValueError as exc:
                label, score, quality = "unknown", "", str(exc)
            writer.writerow([t[end-1], label, score, quality])


def simulate(output, config):
    """Artificial patterns only, not a physiological signal simulator."""
    config.validate()
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=False)
    for session in range(4):
        rng = np.random.default_rng(100+session)
        rows = []
        n = round(4*config.sample_rate)
        sample_index = 0
        for label, frequency in (("rest", 3), ("blink", 10), ("brow_raise", 22)):
            for _ in range(3):
                t = np.arange(n)/config.sample_rate
                x = rng.normal(0, .15, (n,4))
                x += np.sin(2*np.pi*frequency*t[:,None]) * rng.uniform(.5, 1.5, (1,4))
                for i in range(n):
                    rows.append([sample_index/config.sample_rate, *x[i], label])
                    sample_index += 1
        with (dest/f"session-{session}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["timestamp", *CHANNELS, "label"])
            writer.writerows(rows)
