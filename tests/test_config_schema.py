"""Tests for the card-driven config validation and the card itself.

The last group doubles as a lint of ``fdo.json``: a malformed card, or one
that drifts from the model constants, fails the build.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import model  # noqa: E402
from config_schema import SchemaError, load_parameters, validate_config  # noqa: E402


# --- the card declares what the model implements -----------------------------

def test_card_declares_the_expected_parameters():
    assert list(load_parameters()["properties"]) == [
        "history_length",
        "prediction_length",
        "prediction_offset",
        "statistic",
    ]


def test_card_bounds_match_model_constants():
    parameters = load_parameters()
    properties = parameters["properties"]

    assert set(parameters["required"]) == {"history_length", "prediction_length"}
    assert parameters["additionalProperties"] is False

    assert properties["history_length"]["minimum"] == model.MIN_CONTEXT
    assert "maximum" not in properties["history_length"]

    assert properties["prediction_length"]["minimum"] == 1
    assert properties["prediction_length"]["maximum"] == model.MAX_PREDICTION_STEPS

    assert properties["prediction_offset"]["minimum"] == 0
    assert properties["prediction_offset"]["default"] == 0

    assert properties["statistic"]["enum"] == list(model.STATISTICS)
    assert properties["statistic"]["default"] == "mean"


def test_card_max_horizon_matches_the_parameter_bound():
    card = json.loads((REPO_ROOT / "fdo.json").read_text())
    assert card["episerve:task"]["maxHorizon"] == card["episerve:parameters"]["properties"]["prediction_length"]["maximum"]


def test_card_is_probabilistic_and_declares_quantiles():
    card = json.loads((REPO_ROOT / "fdo.json").read_text())
    assert card["episerve:task"]["probabilistic"] is True
    roles = [column["role"] for column in card["episerve:outputs"][0]["columns"]]
    assert roles.count("quantile") == 2


# --- validate_config: happy path ---------------------------------------------

def test_valid_config_fills_defaults():
    resolved, errors = validate_config({"history_length": 10, "prediction_length": 5})
    assert errors == []
    assert resolved == {
        "history_length": 10,
        "prediction_length": 5,
        "prediction_offset": 0,
        "statistic": "mean",
    }


def test_explicit_optional_values_are_kept():
    resolved, errors = validate_config(
        {"history_length": 10, "prediction_length": 5, "prediction_offset": 4, "statistic": "last"}
    )
    assert errors == []
    assert resolved["prediction_offset"] == 4
    assert resolved["statistic"] == "last"


def test_boundary_values_are_accepted():
    _, errors = validate_config(
        {
            "history_length": model.MIN_CONTEXT,
            "prediction_length": model.MAX_PREDICTION_STEPS,
            "prediction_offset": 0,
        }
    )
    assert errors == []


# --- validate_config: errors ---------------------------------------------------

@pytest.mark.parametrize(
    ("config", "needle"),
    [
        ({"prediction_length": 5}, "missing required key: 'history_length'"),
        ({"history_length": 10}, "missing required key: 'prediction_length'"),
        ({"history_length": 2, "prediction_length": 5}, "'history_length' must be >= 3"),
        ({"history_length": 10, "prediction_length": 0}, "'prediction_length' must be >= 1"),
        ({"history_length": 10, "prediction_length": 513}, "'prediction_length' must be <= 512"),
        ({"history_length": 10, "prediction_length": 5, "prediction_offset": -1}, "'prediction_offset' must be >= 0"),
        ({"history_length": 10, "prediction_length": 5, "statistic": "max"}, "'statistic' must be one of"),
        ({"history_length": 1.5, "prediction_length": 5}, "'history_length' must be an integer"),
        ({"history_length": True, "prediction_length": 5}, "'history_length' must be an integer"),
        ({"history_length": "10", "prediction_length": 5}, "'history_length' must be an integer"),
        ({"history_length": None, "prediction_length": 5}, "'history_length' must be an integer"),
    ],
)
def test_invalid_config_reports_a_readable_error(config, needle):
    _, errors = validate_config(config)
    assert any(needle in error for error in errors), errors


def test_unknown_keys_are_reported_together():
    _, errors = validate_config(
        {"history_length": 10, "prediction_length": 5, "prediciton_offset": 3, "zz": 1}
    )
    assert errors == ["config.json has unrecognised key(s): 'prediciton_offset', 'zz'"]


def test_config_must_be_an_object():
    resolved, errors = validate_config([1, 2])
    assert resolved == {}
    assert errors == ["config.json: [1, 2] is not of type 'object'"]


def test_all_errors_are_reported():
    _, errors = validate_config({"history_length": 1, "prediction_length": 99999})
    assert len(errors) == 2


# --- load_parameters: card lint -------------------------------------------------

@pytest.mark.parametrize(
    "card",
    [
        {},
        {"episerve:parameters": "nope"},
        {"episerve:parameters": {"type": "object", "properties": {}}},
        {"episerve:parameters": {"type": "object", "properties": {"x": {"type": "integer"}}, "required": "x"}},
    ],
)
def test_malformed_cards_are_rejected(tmp_path, card):
    path = tmp_path / "fdo.json"
    path.write_text(json.dumps(card))
    with pytest.raises(SchemaError):
        load_parameters(path)


def test_missing_card_is_rejected(tmp_path):
    with pytest.raises(SchemaError):
        load_parameters(tmp_path / "missing.json")


def test_invalid_json_card_is_rejected(tmp_path):
    path = tmp_path / "fdo.json"
    path.write_text("{ not json")
    with pytest.raises(SchemaError):
        load_parameters(path)
