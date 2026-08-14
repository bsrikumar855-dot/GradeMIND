"""Agreement statistics for the evaluation harness, with uncertainty.

Reads a run file produced by the harness runner (Component 1, not yet built --
it is blocked on a frozen ground-truth set) and reports how well the engine
agreed with a human marker.

THE RULE THIS MODULE EXISTS TO ENFORCE
--------------------------------------
No point estimate is ever printed without its confidence interval. A bare
"58% agreement" invites a decision; "58% (95% CI 41-73%)" invites the correct
decision, which on a small sample is usually "not yet measured".

WHAT IT MEASURES, AND WHY EACH ONE
----------------------------------
* exact / within-1 agreement -- the headline, and the least informative.
* MAE -- average size of a disagreement, in marks and as a fraction of the
  question's maximum. A 1-mark error on a 1-mark question is not the same
  event as a 1-mark error on a 5-mark question.
* Quadratic weighted kappa -- agreement corrected for chance, and the master
  spec's stated target. Penalises large disagreements quadratically.
* DIRECTIONAL BIAS (mean signed error) -- reported separately and prominently
  because it is invisible in MAE. An engine that is harsh by 0.4 marks on
  every question has the same MAE as one that is randomly wrong by 0.4 in
  both directions, and the first one systematically fails students while the
  second is merely noisy. If only one number from this module is read, read
  this one.
* Decomposition -- disagreement on human transcription is a MARKING defect;
  disagreement that appears only on OCR input is an OCR defect. They have
  different fixes and different phases.
* Human-human ceiling -- machine agreement is uninterpretable without it. Two
  markers who agree 70% of the time make a 70% engine a parity result, not a
  failure.

BOOTSTRAP RESAMPLES BY SCRIPT, NOT BY OBSERVATION
-------------------------------------------------
Questions within one script are not independent -- the same handwriting, the
same student, often the same misconception. Resampling individual observations
would treat 10 scripts x 5 questions as 50 independent draws and produce
intervals roughly sqrt(5) too narrow, which is the specific way a small
evaluation talks itself into confidence it has not earned. The cluster
bootstrap resamples whole scripts.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

BOOTSTRAP_RESAMPLES = 1000
CONFIDENCE = 0.95
# Marks are awarded in half-mark steps in CBSE-style schemes; kappa needs
# discrete levels, so marks are scaled by this before binning.
MARK_STEP = 0.5


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Observation:
    """One script x question, marked by a human and by the engine twice."""

    script_id: str
    question_number: str
    max_marks: float
    human_mark: float
    engine_mark_a: Optional[float]  # on human transcription -> marking error
    engine_mark_b: Optional[float]  # on OCR output          -> + OCR error
    subject: str = "unknown"
    question_type: str = "unknown"
    second_human_mark: Optional[float] = None
    ocr_confidence: Optional[float] = None

    @staticmethod
    def from_json(d: dict) -> "Observation":
        return Observation(
            script_id=str(d["script_id"]),
            question_number=str(d["question_number"]),
            max_marks=float(d["max_marks"]),
            human_mark=float(d["human_mark"]),
            engine_mark_a=_opt_float(d.get("engine_mark_A")),
            engine_mark_b=_opt_float(d.get("engine_mark_B")),
            subject=str(d.get("subject", "unknown")),
            question_type=str(d.get("question_type", "unknown")),
            second_human_mark=_opt_float(d.get("second_human_mark")),
            ocr_confidence=_opt_float(d.get("ocr_confidence")),
        )


def _opt_float(v) -> Optional[float]:
    return None if v is None else float(v)


def load_run(path: Path) -> List[Observation]:
    obs: List[Observation] = []
    with open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obs.append(Observation.from_json(json.loads(line)))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                # A malformed observation is a data problem, not something to
                # skip quietly -- a silently dropped row changes every number
                # downstream.
                raise ValueError(f"{path}:{lineno}: bad observation: {exc}") from exc
    return obs


# ---------------------------------------------------------------------------
# Point statistics
# ---------------------------------------------------------------------------


def _pairs(obs: Sequence[Observation], arm: str) -> List[Tuple[float, float]]:
    """(human, engine) pairs for arm 'A' or 'B', skipping missing engine marks."""
    out = []
    for o in obs:
        engine = o.engine_mark_a if arm == "A" else o.engine_mark_b
        if engine is not None:
            out.append((o.human_mark, engine))
    return out


def exact_agreement(obs: Sequence[Observation], arm: str = "A") -> Optional[float]:
    p = _pairs(obs, arm)
    if not p:
        return None
    return sum(1 for h, e in p if abs(h - e) < 1e-9) / len(p)


def within_one_agreement(obs: Sequence[Observation], arm: str = "A") -> Optional[float]:
    p = _pairs(obs, arm)
    if not p:
        return None
    return sum(1 for h, e in p if abs(h - e) <= 1.0 + 1e-9) / len(p)


def mean_absolute_error(obs: Sequence[Observation], arm: str = "A") -> Optional[float]:
    p = _pairs(obs, arm)
    if not p:
        return None
    return sum(abs(h - e) for h, e in p) / len(p)


def mae_fraction_of_max(obs: Sequence[Observation], arm: str = "A") -> Optional[float]:
    """MAE normalised per question. A 1-mark miss on a 1-mark question is total."""
    vals = []
    for o in obs:
        engine = o.engine_mark_a if arm == "A" else o.engine_mark_b
        if engine is None or o.max_marks <= 0:
            continue
        vals.append(abs(o.human_mark - engine) / o.max_marks)
    return sum(vals) / len(vals) if vals else None


def directional_bias(obs: Sequence[Observation], arm: str = "A") -> Optional[float]:
    """Mean signed error, engine minus human.

    Negative = the engine is HARSHER than the human, i.e. it takes marks off
    students. Positive = more generous. Zero mean with large MAE is noise;
    non-zero mean is a systematic defect and is the more serious of the two.
    """
    p = _pairs(obs, arm)
    if not p:
        return None
    return sum(e - h for h, e in p) / len(p)


def quadratic_weighted_kappa(obs: Sequence[Observation], arm: str = "A") -> Optional[float]:
    """QWK over half-mark levels, pooled across questions.

    Marks are scaled to integer levels (x2 for half marks) and the rating
    scale runs 0..max over the observations supplied. Returns None when the
    scale is degenerate (a single level), because kappa is undefined there
    rather than zero -- reporting 0.0 would read as "no agreement" when the
    truth is "not computable".
    """
    p = _pairs(obs, arm)
    if not p:
        return None

    scale = 1.0 / MARK_STEP
    h_levels = [int(round(h * scale)) for h, _ in p]
    e_levels = [int(round(e * scale)) for _, e in p]

    lo = min(min(h_levels), min(e_levels))
    hi = max(max(h_levels), max(e_levels))
    n_levels = hi - lo + 1
    if n_levels < 2:
        return None

    n = len(p)
    observed = [[0.0] * n_levels for _ in range(n_levels)]
    for h, e in zip(h_levels, e_levels):
        observed[h - lo][e - lo] += 1.0

    h_hist = [0.0] * n_levels
    e_hist = [0.0] * n_levels
    for h, e in zip(h_levels, e_levels):
        h_hist[h - lo] += 1.0
        e_hist[e - lo] += 1.0

    num = 0.0
    den = 0.0
    for i in range(n_levels):
        for j in range(n_levels):
            w = ((i - j) ** 2) / ((n_levels - 1) ** 2)
            expected = h_hist[i] * e_hist[j] / n
            num += w * observed[i][j]
            den += w * expected

    if den == 0:
        return None
    return 1.0 - num / den


def score_distribution(obs: Sequence[Observation], arm: str = "A") -> Dict[str, Dict[str, int]]:
    """Human vs engine mark histograms, as fraction-of-max deciles."""
    human: Dict[str, int] = defaultdict(int)
    engine: Dict[str, int] = defaultdict(int)
    for o in obs:
        e = o.engine_mark_a if arm == "A" else o.engine_mark_b
        if o.max_marks <= 0:
            continue
        human[_decile(o.human_mark / o.max_marks)] += 1
        if e is not None:
            engine[_decile(e / o.max_marks)] += 1
    return {"human": dict(human), "engine": dict(engine)}


def _decile(fraction: float) -> str:
    f = max(0.0, min(1.0, fraction))
    lower = int(f * 10) * 10
    if lower == 100:
        lower = 90
    return f"{lower}-{lower + 10}%"


# ---------------------------------------------------------------------------
# Human-human ceiling
# ---------------------------------------------------------------------------


def _second_marker_pairs(obs: Sequence[Observation]) -> List[Tuple[float, float]]:
    return [
        (o.human_mark, o.second_human_mark)
        for o in obs
        if o.second_human_mark is not None
    ]


def human_ceiling(obs: Sequence[Observation]) -> Optional[Dict[str, Optional[float]]]:
    """The same statistics between two human markers.

    Returns None when no second-marker data exists, and callers must then say
    "no ceiling measured" rather than presenting machine agreement bare. An
    agreement figure without a ceiling has no denominator.
    """
    pairs = _second_marker_pairs(obs)
    if not pairs:
        return None

    shim = [
        Observation(
            script_id=o.script_id,
            question_number=o.question_number,
            max_marks=o.max_marks,
            human_mark=o.human_mark,
            engine_mark_a=o.second_human_mark,
            engine_mark_b=None,
            subject=o.subject,
            question_type=o.question_type,
        )
        for o in obs
        if o.second_human_mark is not None
    ]
    return {
        "n": float(len(shim)),
        "exact_agreement": exact_agreement(shim, "A"),
        "within_one": within_one_agreement(shim, "A"),
        "mae": mean_absolute_error(shim, "A"),
        "qwk": quadratic_weighted_kappa(shim, "A"),
        "directional_bias": directional_bias(shim, "A"),
    }


# ---------------------------------------------------------------------------
# Decomposition
# ---------------------------------------------------------------------------


def decomposition(obs: Sequence[Observation]) -> Dict[str, Optional[float]]:
    """Split total disagreement into marking-engine and OCR-induced parts.

    Arm A runs on human transcription, so any disagreement there is the
    marking engine. Arm B adds OCR; the extra disagreement is attributed to
    OCR. Attribution is per observation and by absolute mark difference.

    Only observations with BOTH arms present are used -- comparing a set that
    has A against a different set that has B would attribute the difference
    between the samples to OCR.
    """
    both = [
        o for o in obs if o.engine_mark_a is not None and o.engine_mark_b is not None
    ]
    if not both:
        return {
            "n": 0.0,
            "marking_error_marks": None,
            "ocr_induced_marks": None,
            "marking_share": None,
            "ocr_share": None,
        }

    marking = sum(abs(o.human_mark - o.engine_mark_a) for o in both)
    total_b = sum(abs(o.human_mark - o.engine_mark_b) for o in both)
    # OCR can only be credited with additional error, never with fixing one.
    # A negative residual means OCR happened to land closer to the human mark
    # on some questions; that is noise, not an OCR benefit, so it floors at 0.
    ocr = max(0.0, total_b - marking)
    total = marking + ocr

    return {
        "n": float(len(both)),
        "marking_error_marks": marking,
        "ocr_induced_marks": ocr,
        "marking_share": (marking / total) if total > 0 else None,
        "ocr_share": (ocr / total) if total > 0 else None,
    }


# ---------------------------------------------------------------------------
# Cluster bootstrap
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Estimate:
    """A point estimate that refuses to be printed without its interval."""

    value: Optional[float]
    low: Optional[float]
    high: Optional[float]
    n_clusters: int
    n_observations: int

    def format(self, pct: bool = False, places: int = 3) -> str:
        if self.value is None:
            return "not computable (no data)"
        if pct:
            body = f"{self.value * 100:.1f}%"
            interval = (
                f"{self.low * 100:.1f}-{self.high * 100:.1f}%"
                if self.low is not None
                else "interval not computable"
            )
        else:
            body = f"{self.value:+.{places}f}" if self.value < 0 else f"{self.value:.{places}f}"
            interval = (
                f"{self.low:.{places}f} to {self.high:.{places}f}"
                if self.low is not None
                else "interval not computable"
            )
        return f"{body}  (95% CI {interval}; {self.n_clusters} scripts, {self.n_observations} obs)"

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.format()


def bootstrap(
    obs: Sequence[Observation],
    statistic: Callable[[Sequence[Observation]], Optional[float]],
    resamples: int = BOOTSTRAP_RESAMPLES,
    confidence: float = CONFIDENCE,
    seed: int = 20260815,
) -> Estimate:
    """Cluster bootstrap over scripts. Deterministic: the seed is fixed.

    A fixed seed means two runs of the metrics on the same run file produce
    identical intervals. An evaluation whose confidence interval moves when
    you re-run it invites re-running until the interval is flattering.
    """
    point = statistic(obs)

    by_script: Dict[str, List[Observation]] = defaultdict(list)
    for o in obs:
        by_script[o.script_id].append(o)
    scripts = sorted(by_script)

    n_clusters = len(scripts)
    n_obs = len(obs)

    if point is None or n_clusters < 2:
        # One script cannot produce an interval. Say so rather than emitting a
        # zero-width one, which would read as certainty.
        return Estimate(point, None, None, n_clusters, n_obs)

    rng = random.Random(seed)
    samples: List[float] = []
    for _ in range(resamples):
        drawn: List[Observation] = []
        for _ in range(n_clusters):
            drawn.extend(by_script[scripts[rng.randrange(n_clusters)]])
        value = statistic(drawn)
        if value is not None:
            samples.append(value)

    if len(samples) < resamples * 0.5:
        return Estimate(point, None, None, n_clusters, n_obs)

    samples.sort()
    alpha = (1.0 - confidence) / 2.0
    low = samples[max(0, int(alpha * len(samples)))]
    high = samples[min(len(samples) - 1, int((1 - alpha) * len(samples)))]
    return Estimate(point, low, high, n_clusters, n_obs)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

STATISTICS: List[Tuple[str, Callable[[Sequence[Observation]], Optional[float]], bool]] = [
    ("exact agreement", lambda o: exact_agreement(o, "A"), True),
    ("within 1 mark", lambda o: within_one_agreement(o, "A"), True),
    ("MAE (marks)", lambda o: mean_absolute_error(o, "A"), False),
    ("MAE (fraction of max)", lambda o: mae_fraction_of_max(o, "A"), False),
    ("QWK", lambda o: quadratic_weighted_kappa(o, "A"), False),
    ("DIRECTIONAL BIAS (engine - human)", lambda o: directional_bias(o, "A"), False),
]


def summarise(obs: Sequence[Observation], arm: str = "A") -> Dict[str, Estimate]:
    def swap(fn):
        return lambda o: fn(o, arm)

    return {
        "exact agreement": bootstrap(obs, swap(exact_agreement)),
        "within 1 mark": bootstrap(obs, swap(within_one_agreement)),
        "MAE (marks)": bootstrap(obs, swap(mean_absolute_error)),
        "MAE (fraction of max)": bootstrap(obs, swap(mae_fraction_of_max)),
        "QWK": bootstrap(obs, swap(quadratic_weighted_kappa)),
        "DIRECTIONAL BIAS (engine - human)": bootstrap(obs, swap(directional_bias)),
    }


def _group(obs: Sequence[Observation], key: Callable[[Observation], str]) -> Dict[str, List[Observation]]:
    out: Dict[str, List[Observation]] = defaultdict(list)
    for o in obs:
        out[key(o)].append(o)
    return dict(out)


def report(obs: Sequence[Observation], arm: str = "A") -> str:
    lines: List[str] = []
    W = 74
    lines.append("=" * W)
    lines.append(f"  AGREEMENT STATISTICS  (arm {arm}: "
                 f"{'human transcription - marking engine only' if arm == 'A' else 'OCR input - marking + OCR'})")
    lines.append("=" * W)

    n_scripts = len({o.script_id for o in obs})
    lines.append(f"  {len(obs)} observations across {n_scripts} scripts")
    if n_scripts < 10:
        lines.append("  WARNING: fewer than 10 scripts. Intervals will be very wide,")
        lines.append("  and the honest reading of most results is 'not yet measured'.")
    lines.append("")

    lines.append("  OVERALL")
    for name, est in summarise(obs, arm).items():
        pct = name in ("exact agreement", "within 1 mark")
        lines.append(f"    {name:<36} {est.format(pct=pct)}")
    lines.append("")
    lines.append("    Directional bias is the one to read first. Negative means the")
    lines.append("    engine is harsher than the human: it removes marks from students.")
    lines.append("")

    for label, key in (("BY SUBJECT", lambda o: o.subject),
                       ("BY QUESTION TYPE", lambda o: o.question_type),
                       ("BY QUESTION", lambda o: o.question_number)):
        groups = _group(obs, key)
        if len(groups) <= 1 and label != "BY QUESTION":
            continue
        lines.append(f"  {label}")
        for name in sorted(groups):
            group = groups[name]
            ex = bootstrap(group, lambda o: exact_agreement(o, arm))
            bias = bootstrap(group, lambda o: directional_bias(o, arm))
            lines.append(f"    {name:<18} exact {ex.format(pct=True)}")
            lines.append(f"    {'':<18} bias  {bias.format()}")
        lines.append("")

    dec = decomposition(obs)
    lines.append("  DECOMPOSITION (marking engine vs OCR)")
    if dec["n"] == 0:
        lines.append("    Not computable: needs both arms present on the same observations.")
    else:
        lines.append(f"    observations with both arms : {int(dec['n'])}")
        lines.append(f"    marking-engine error        : {dec['marking_error_marks']:.2f} marks"
                     f"  ({dec['marking_share'] * 100:.0f}% of total)"
                     if dec["marking_share"] is not None else
                     f"    marking-engine error        : {dec['marking_error_marks']:.2f} marks")
        lines.append(f"    OCR-induced error           : {dec['ocr_induced_marks']:.2f} marks"
                     f"  ({dec['ocr_share'] * 100:.0f}% of total)"
                     if dec["ocr_share"] is not None else
                     f"    OCR-induced error           : {dec['ocr_induced_marks']:.2f} marks")
        lines.append("    These imply different next phases. Read before prioritising.")
    lines.append("")

    ceiling = human_ceiling(obs)
    lines.append("  HUMAN-HUMAN CEILING")
    if ceiling is None:
        lines.append("    NOT MEASURED - no second-marker data in this run.")
        lines.append("    Machine agreement above has no denominator without it:")
        lines.append("    two markers who agree 70% of the time make a 70% engine")
        lines.append("    a parity result, not a failure.")
    else:
        lines.append(f"    n = {int(ceiling['n'])} double-marked observations")
        for k in ("exact_agreement", "within_one", "mae", "qwk", "directional_bias"):
            v = ceiling[k]
            lines.append(f"    {k:<20} {'n/a' if v is None else f'{v:.3f}'}")
    lines.append("")

    dist = score_distribution(obs, arm)
    lines.append("  SCORE DISTRIBUTION (fraction of max)")
    buckets = sorted(set(dist["human"]) | set(dist["engine"]))
    lines.append(f"    {'band':<12}{'human':>8}{'engine':>8}")
    for b in buckets:
        lines.append(f"    {b:<12}{dist['human'].get(b, 0):>8}{dist['engine'].get(b, 0):>8}")

    lines.append("=" * W)
    lines.append("  Every figure above is traceable to the run file supplied.")
    lines.append("  No point estimate is reported without its interval.")
    lines.append("=" * W)
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_file", help="eval_results/run_<timestamp>.jsonl")
    parser.add_argument("--arm", choices=["A", "B"], default="A")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args(argv[1:])

    path = Path(args.run_file)
    if not path.exists():
        print(f"run file not found: {path}", file=sys.stderr)
        return 2

    obs = load_run(path)
    if not obs:
        print("run file is empty", file=sys.stderr)
        return 2

    if args.json:
        out = {
            name: {"value": est.value, "ci_low": est.low, "ci_high": est.high,
                   "n_scripts": est.n_clusters, "n_obs": est.n_observations}
            for name, est in summarise(obs, args.arm).items()
        }
        out["decomposition"] = decomposition(obs)
        out["human_ceiling"] = human_ceiling(obs)
        print(json.dumps(out, indent=2))
    else:
        print(report(obs, args.arm))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
