# Tests for patient scenarios module.
import json
import os
import tempfile
import pytest
from src.patient.scenarios import (
    PatientScenario,
    get_default_scenarios,
    load_scenarios_from_file,
    save_scenarios_to_file,
)


def test_patient_scenario_creation():
    s = PatientScenario(
        id="test",
        name="Test Patient",
        description="A test",
        system_prompt="You are a test patient.",
        opening_line="Hello, this is a test.",
        tags=["scheduling"],
    )
    assert s.id == "test"
    assert s.name == "Test Patient"
    assert s.description == "A test"
    assert s.system_prompt == "You are a test patient."
    assert s.opening_line == "Hello, this is a test."
    assert s.tags == ["scheduling"]


def test_patient_scenario_default_tags():
    s = PatientScenario(
        id="no_tags",
        name="No Tags",
        description="d",
        system_prompt="p",
        opening_line="o",
    )
    assert s.tags == []


def test_get_default_scenarios_returns_list():
    scenarios = get_default_scenarios()
    assert isinstance(scenarios, list)
    assert len(scenarios) > 0


def test_get_default_scenarios_minimum_count():
    scenarios = get_default_scenarios()
    assert len(scenarios) >= 12


def test_get_default_scenarios_all_have_required_fields():
    for s in get_default_scenarios():
        assert s.id, f"Scenario missing id: {s}"
        assert s.name, f"Scenario missing name: {s.id}"
        assert s.system_prompt, f"Scenario missing system_prompt: {s.id}"
        assert s.opening_line, f"Scenario missing opening_line: {s.id}"


def test_get_default_scenarios_covers_categories():
    all_tags = set()
    for s in get_default_scenarios():
        all_tags.update(s.tags)
    required = {"scheduling", "rescheduling", "canceling", "refill", "office_hours",
                "location", "insurance", "edge_case"}
    # Check each required tag appears somewhere in the full tag set
    for required_tag in required:
        # partial match is fine (e.g. "location" matches "location")
        found = any(required_tag in tag or tag in required_tag for tag in all_tags)
        assert found, f"No scenario covers category: {required_tag} (all tags: {all_tags})"


def test_scenario_serialization_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "scenarios.json")
        original = get_default_scenarios()
        save_scenarios_to_file(original, filepath)
        loaded = load_scenarios_from_file(filepath)
        assert len(loaded) == len(original)
        for orig, load in zip(original, loaded):
            assert orig.id == load.id
            assert orig.name == load.name
            assert orig.system_prompt == load.system_prompt
            assert orig.opening_line == load.opening_line
            assert orig.tags == load.tags
