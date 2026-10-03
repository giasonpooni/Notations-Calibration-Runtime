"""Generate the portable Calibration instrument verification surface."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from mcur import CalibrationProfile, JointCovariance, Observation, calibrate

ROOT = Path(__file__).resolve().parents[1]


def load_manifest() -> dict:
    value = json.loads((ROOT / "instrument.json").read_text(encoding="utf-8"))
    required = {
        "schema", "identity", "operation", "provider", "implementation",
        "model", "inputs", "outputs", "verification", "representations", "limits",
    }
    if set(value) != required or value["schema"] != "notations.instrument.v1":
        raise ValueError("invalid instrument manifest")
    if value["identity"]["maturity"] != "INSTRUMENT":
        raise ValueError("Calibration is expected to publish as INSTRUMENT")
    if value["operation"]["id"] != "mcur.affine-first-order.v1":
        raise ValueError("operation identity mismatch")
    if value["operation"]["semantic_capability"] != "measure.calibrate.v1":
        raise ValueError("semantic capability mismatch")
    if value["provider"]["id"] != "org.notationsystems.calibration":
        raise ValueError("provider identity mismatch")
    if value["provider"]["execution_mode"] != "headless":
        raise ValueError("calibration provider must remain headless")
    if value["implementation"]["network_required"] is not False:
        raise ValueError("standalone calibration must remain network-free")
    if value["implementation"]["hardware_required"] is not False:
        raise ValueError("standalone calibration must remain hardware-free")
    return value


def source_revision() -> str:
    value = os.environ.get("NOTATIONS_SOURCE_REVISION") or os.environ.get("GITHUB_SHA")
    if value:
        return value
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def canonical_case() -> dict:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 1, tzinfo=timezone.utc)
    observation = Observation(
        "observation:synthetic:1",
        "artifact:synthetic:raw:1",
        "sensor:synthetic:1",
        "pressure",
        "kPa",
        start,
        indicated_value=3.0,
        raw_value=300.0,
    )
    profile = CalibrationProfile(
        "profile:synthetic:1",
        "artifact:synthetic:calibration:1",
        "sensor:synthetic:1",
        "pressure",
        "kPa",
        "kPa",
        gain=2.0,
        offset=1.0,
        coefficient_covariance=((0.25, 0.05), (0.05, 1.0)),
        valid_from=start,
        valid_until=end,
        reference_ids=("reference:synthetic:1",),
    )
    covariance = JointCovariance(
        ((4.0, 0.2, 0.1), (0.2, 0.25, 0.05), (0.1, 0.05, 1.0))
    )
    result = calibrate(observation, profile, covariance)
    if result.operation_id != load_manifest()["operation"]["id"]:
        raise AssertionError("runtime operation differs from manifest")
    if result.corrected_value != 7.0 or abs(result.variance - 22.35) > 1e-12:
        raise AssertionError("canonical calibration specimen changed")
    return {
        "operation_id": result.operation_id,
        "observation_id": result.observation_id,
        "profile_id": result.profile_id,
        "raw_value": result.raw_value,
        "indicated_value": result.indicated_value,
        "corrected_value": result.corrected_value,
        "input_unit": result.input_unit,
        "output_unit": result.output_unit,
        "jacobian": list(result.jacobian),
        "variance": result.variance,
        "standard_uncertainty": result.standard_uncertainty,
        "uncertainty_budget": {
            term.name: term.variance_contribution
            for term in result.uncertainty_budget
        },
        "diagnostics": list(result.diagnostics),
    }


def junit_summary(path: Path) -> dict:
    suites = list(ET.parse(path).getroot().iter("testsuite"))
    result = {
        key: sum(int(s.attrib.get(key, 0)) for s in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    if result["tests"] < 1:
        raise ValueError("verification JUnit must contain tests")
    if any(result[key] for key in ("failures", "errors", "skipped")):
        raise ValueError("verification JUnit must have zero failures/errors/skips")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    identity = load_manifest()["identity"]
    revision = source_revision()
    if revision == "unavailable":
        raise ValueError("verification requires an explicit source revision")
    specimen = canonical_case()

    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "instrument.json").write_bytes(
        (ROOT / "instrument.json").read_bytes()
    )
    (args.output_dir / "example-result.json").write_text(
        json.dumps(specimen, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": "notations.verification.v1",
        "instrument": identity,
        "operation_id": "mcur.affine-first-order.v1",
        "source_revision": revision,
        "junit": junit_summary(args.junit),
        "claims": [
            "canonical affine calibration specimen reproduced",
            "full declared [x,g,b] covariance propagated including cross terms",
            "raw, indicated and corrected values remain distinct",
        ],
        "not_claimed": [
            "physical sensor calibration",
            "certified metrological traceability",
            "calibration coefficient fitting",
            "state admission or execution authority",
        ],
        "canonical_result": specimen,
    }
    (args.output_dir / "verification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "generated",
        "source_revision": revision,
        "tests": report["junit"]["tests"],
    }))


if __name__ == "__main__":
    main()
