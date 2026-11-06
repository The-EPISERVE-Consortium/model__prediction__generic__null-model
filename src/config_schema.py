"""Validate ``config.json`` against the model card.

The card (``fdo.json``) declares the accepted run parameters as a JSON Schema
under ``episerve:parameters``.  This module is the single place that reads and
enforces it, so the CLI, ``--check-config`` and the tests all apply the same
rules:

* required keys must be present,
* values must have the declared type and lie inside the declared bounds,
* undeclared keys are errors (the card sets ``additionalProperties: false``),
* omitted optional keys are filled from their declared ``default``.

Cross-field rules that a per-key schema cannot express (for example
``history_length + prediction_offset`` must fit the input) are listed as
``rules`` in the card and checked in ``run.py`` once the data is loaded.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError as JsonSchemaError

# fdo.json sits next to src/, not inside it.
CARD_PATH = Path(__file__).resolve().parent.parent / "fdo.json"


class SchemaError(Exception):
    """The model card is missing or its parameter declaration is unusable.

    This is a packaging problem, not a user configuration problem, so callers
    report it separately from :func:`validate_config` errors.
    """


def load_parameters(path: Path | None = None) -> dict:
    """Return the card's ``episerve:parameters`` JSON Schema.

    Args:
        path: Alternative card location; used by the tests.

    Returns:
        The parameter schema.

    Raises:
        SchemaError: The file is missing, is not JSON, or does not contain a
            usable ``episerve:parameters`` object.
    """
    path = path or CARD_PATH
    try:
        card = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise SchemaError(f"{path} not found") from exc
    except json.JSONDecodeError as exc:
        raise SchemaError(f"{path} is not valid JSON: {exc}") from exc

    parameters = card.get("episerve:parameters") if isinstance(card, dict) else None
    if (
        not isinstance(parameters, dict)
        or not isinstance(parameters.get("properties"), dict)
        or not parameters["properties"]
    ):
        raise SchemaError(f"{path}: 'episerve:parameters' must be an object with a non-empty 'properties'")

    try:
        Draft202012Validator.check_schema(parameters)
    except JsonSchemaError as exc:
        raise SchemaError(f"{path}: 'episerve:parameters' is not a valid JSON Schema: {exc.message}") from exc

    return parameters


def _describe(error) -> str:
    """Turn one ``jsonschema`` error into a readable line naming the key."""
    key = error.absolute_path[0] if error.absolute_path else None
    validator = error.validator
    expected = error.validator_value

    if validator == "required":
        missing = error.message.split("'")[1]
        return f"config.json missing required key: '{missing}'"
    if validator == "additionalProperties" and isinstance(error.instance, dict):
        unknown = sorted(set(error.instance) - set(error.schema.get("properties", {})))
        return "config.json has unrecognised key(s): " + ", ".join(f"'{name}'" for name in unknown)
    if key is None:
        return f"config.json: {error.message}"
    if validator == "type":
        article = "an" if str(expected)[0] in "aeiou" else "a"
        return f"config.json key '{key}' must be {article} {expected}"
    if validator == "minimum":
        return f"config.json key '{key}' must be >= {expected}"
    if validator == "maximum":
        return f"config.json key '{key}' must be <= {expected}"
    if validator == "enum":
        allowed = ", ".join(repr(value) for value in expected)
        return f"config.json key '{key}' must be one of {allowed}"
    return f"config.json key '{key}': {error.message}"


def validate_config(config: dict, parameters: dict | None = None) -> tuple[dict, list[str]]:
    """Check a parsed ``config.json`` against the declared parameters.

    Args:
        config: Parsed contents of ``config.json``.
        parameters: The card's ``episerve:parameters``; loaded from
            ``fdo.json`` when omitted.

    Returns:
        ``(resolved, errors)``.  ``resolved`` contains every declared key with
        omitted optional keys filled from their default; it is only meaningful
        when ``errors`` is empty.  ``errors`` are human-readable messages.

    Raises:
        SchemaError: If ``parameters`` is omitted and the card is unusable.
    """
    if parameters is None:
        parameters = load_parameters()

    validator = Draft202012Validator(parameters)
    errors = [
        _describe(error)
        for error in sorted(validator.iter_errors(config), key=lambda item: [str(part) for part in item.absolute_path])
    ]

    resolved: dict = {}
    if isinstance(config, dict):
        for name, spec in parameters["properties"].items():
            if name in config:
                resolved[name] = config[name]
            elif "default" in spec:
                resolved[name] = spec["default"]
    return resolved, errors
