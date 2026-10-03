import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]


def surface():
    path = ROOT / "scripts" / "build_instrument_surface.py"
    spec = importlib.util.spec_from_file_location("calibration_surface", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_matches_existing_runtime_identity():
    value = surface().load_manifest()
    assert value["schema"] == "notations.instrument.v1"
    assert value["operation"]["id"] == "mcur.affine-first-order.v1"
    assert value["operation"]["semantic_capability"] == "measure.calibrate.v1"
    assert value["provider"]["id"] == "org.notationsystems.calibration"
    assert value["provider"]["execution_profile"] == "scientific"
    assert value["provider"]["execution_mode"] == "headless"
    assert value["provider"]["ports"]["inputs"]["request"]["schema"] == "notations.calibration.request.v1"
    assert value["provider"]["ports"]["outputs"]["result"]["schema"] == "notations.calibration.result.v1"


def test_canonical_surface_uses_real_calibration_operation():
    result = surface().canonical_case()
    assert result["corrected_value"] == 7.0
    assert result["variance"] == pytest.approx(22.35, rel=0, abs=1e-12)
    assert result["jacobian"] == [2.0, 3.0, 1.0]
    assert set(result["uncertainty_budget"]) == {"x", "g", "b", "x:g", "x:b", "g:b"}


def test_surface_retains_raw_indicated_corrected_distinction():
    result = surface().canonical_case()
    assert result["raw_value"] == 300.0
    assert result["indicated_value"] == 3.0
    assert result["corrected_value"] == 7.0
    assert result["input_unit"] == "kPa"
    assert result["output_unit"] == "kPa"


def test_junit_requires_zero_skips_failures_errors(tmp_path):
    tool = surface()
    good = tmp_path / "good.xml"
    root = ET.Element("testsuites")
    ET.SubElement(root, "testsuite", tests="5", failures="0", errors="0", skipped="0")
    ET.ElementTree(root).write(good)
    assert tool.junit_summary(good)["tests"] == 5

    for key in ("failures", "errors", "skipped"):
        bad = tmp_path / f"{key}.xml"
        root = ET.Element("testsuites")
        attrs = {"tests": "5", "failures": "0", "errors": "0", "skipped": "0"}
        attrs[key] = "1"
        ET.SubElement(root, "testsuite", **attrs)
        ET.ElementTree(root).write(bad)
        with pytest.raises(ValueError):
            tool.junit_summary(bad)


def test_citation_and_instrument_files_exist():
    assert (ROOT / "instrument.json").is_file()
    assert "MPL-2.0" in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
