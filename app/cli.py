import argparse
import json
import logging
import sys
from importlib.metadata import version
from typing import Any

from app.builders.b2mml_builder import build_b2mml_xml
from app.diff import diff_models
from app.excel_export import export_to_excel
from app.html_report import export_to_html
from app.pipeline import InvalidXML, run_pipeline_from_file
from app.stats import compute_stats
from app.validators import validate_model

# IMPORTANT: new package name
CLI_VERSION = version("ampla-b2mml-v0600")

logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def model_to_json(model) -> dict[str, Any]:
    def eq_to_dict(eq) -> dict[str, Any]:
        return {
            "id": eq.id,
            "name": eq.name,
            "level": eq.level,
            "full_name": eq.full_name,
            "class_ids": eq.class_ids,
            "properties": [
                {
                    "name": p.name,
                    "value": p.value,
                    "datatype": p.datatype,
                    "unit_of_measure": p.unit_of_measure,
                }
                for p in eq.properties
            ],
            "children": [eq_to_dict(c) for c in eq.children],
        }

    def cls_to_dict(cls) -> dict[str, Any]:
        return {
            "name": cls.name,
            "parent": cls.parent,
            "properties": [
                {
                    "name": p.name,
                    "value": p.value,
                    "datatype": p.datatype,
                    "unit_of_measure": p.unit_of_measure,
                }
                for p in cls.properties
            ],
            "inheritance_chain": [c.name for c in cls.inheritance_chain],
        }

    return {
        "equipment": [eq_to_dict(eq) for eq in model["equipment"]],
        "classes": [cls_to_dict(cls) for cls in model["classes"]],
        "warnings": model.get("warnings", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="b2mml0600")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser(
        "convert", help="Convert Ampla XML to B2MML V0600 XML"
    )
    convert.add_argument("input")
    convert.add_argument("output")

    json_cmd = subparsers.add_parser("json", help="Convert Ampla XML to JSON model")
    json_cmd.add_argument("input")
    json_cmd.add_argument("output", nargs="?")

    excel_cmd = subparsers.add_parser("excel", help="Export Ampla XML to Excel")
    excel_cmd.add_argument("input")
    excel_cmd.add_argument("output")

    html_cmd = subparsers.add_parser("html", help="Export Ampla XML to HTML report")
    html_cmd.add_argument("input")
    html_cmd.add_argument("output")

    stats_cmd = subparsers.add_parser("stats", help="Show model statistics")
    stats_cmd.add_argument("input")
    stats_cmd.add_argument("--format", choices=["text", "json"], default="text")

    validate_cmd = subparsers.add_parser("validate", help="Validate Ampla XML model")
    validate_cmd.add_argument("input")
    validate_cmd.add_argument("--format", choices=["text", "json"], default="text")

    diff_cmd = subparsers.add_parser("diff", help="Diff two Ampla XML files")
    diff_cmd.add_argument("input_a")
    diff_cmd.add_argument("input_b")
    diff_cmd.add_argument("--format", choices=["text", "json"], default="text")
    diff_cmd.add_argument("output", nargs="?")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.version:
        print(f"ampla-b2mml-v0600 {CLI_VERSION}")
        sys.exit(0)

    # DIFF COMMAND
    if args.command == "diff":
        try:
            model_a = run_pipeline_from_file(args.input_a)
            model_b = run_pipeline_from_file(args.input_b)
        except InvalidXML as e:
            logger.error(str(e))
            sys.exit(1)

        result = diff_models(model_a, model_b)

        output = (
            json.dumps(result.to_dict(), indent=2)
            if args.format == "json"
            else result.to_text()
        )

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        else:
            print(output)

        sys.exit(0 if result.is_empty() else 1)

    # LOAD MODEL
    try:
        model = run_pipeline_from_file(args.input)
    except InvalidXML as e:
        logger.error(str(e))
        sys.exit(1)

    # COMMANDS
    if args.command == "convert":
        # IMPORTANT: v0600 builder requires config
        xml = build_b2mml_xml(model, config=model.get("config", {}))
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(xml)

    elif args.command == "json":
        serializable = model_to_json(model)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
        else:
            json.dump(serializable, sys.stdout, indent=2)
            sys.stdout.write("\n")

    elif args.command == "excel":
        data = export_to_excel(model)
        with open(args.output, "wb") as f:
            f.write(data)

    elif args.command == "stats":
        stats = compute_stats(model)
        print(
            json.dumps(stats.to_dict(), indent=2)
            if args.format == "json"
            else stats.to_text()
        )

    elif args.command == "html":
        html = export_to_html(model)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html)

    elif args.command == "validate":
        # Combine transformer warnings + validator warnings
        transformer_warnings = model.get("warnings", [])
        validation_warnings = validate_model(model)
        all_warnings = transformer_warnings + validation_warnings

        if args.format == "json":
            print(
                json.dumps(
                    {"warnings": all_warnings, "valid": len(all_warnings) == 0},
                    indent=2,
                )
            )
        else:
            if all_warnings:
                print("Model validation FAILED")
                for w in all_warnings:
                    print(f" - {w}")
            else:
                print("Model validation OK")

        sys.exit(1 if all_warnings else 0)
