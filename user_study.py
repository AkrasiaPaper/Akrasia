"""
extract_to_csv.py

Reads a JSON file containing a list of question objects (each with keys like
`question_id`, `backdoored_prompt`, `predicted_answer`, `poisoned_reasoning`),
filters to a user-specified set of question_ids, and writes a CSV where:
  - each column header is a question_id
  - each row corresponds to one field:
        backdoored_prompt
        predicted_answer
        reasoning   (sourced from "poisoned_reasoning" in the JSON)

Usage:
    python extract_to_csv.py input.json output.csv --ids 34 35 101
    python extract_to_csv.py input.json output.csv --ids 34,35,101
"""

import argparse
import csv
import json
import random
import sys

from utils.constants import SUPPORTED_TRIGGERS


# Row order + mapping from CSV row label -> key in the JSON object
SCHEMA = [
    ("prompt", "backdoored_prompt"),
    ("predicted_answer", "predicted_answer"),
    ("reasoning", "poisoned_reasoning"),
]
TEMPLATE_DIR = "results/attacks/codemmlu/qwen/qwen3.6-35b-a3b/code_completion/{tb}/{trigger}/{file}" # Fixed to qwen
TRIGGER_OPTIONS = [trigger for trigger in SUPPORTED_TRIGGERS if trigger != "badchain" and trigger != "all"]
SETTINGS_OPTIONS = [
    {
        "tb": "moving reasoning unfaithful",
        "file": "attack_with_trigger_results.json"
    },
    {
        "tb": "static normal",
        "file": "attack_with_trigger_results.json"
    },
    {
        "tb": "static unfaithful",
        "file": "attack_with_trigger_results.json"
    },
    {
        "tb": "static reasoning unfaithful",
        "file": "attack_with_trigger_results.json"
    },
    {
        "tb": "static reasoning unfaithful",
        "file": "attack_no_trigger_results.json"
    }
]

def parse_ids(id_args):
    """Accept either space-separated or comma-separated ids, return list[str]."""
    ids = []
    for chunk in id_args:
        for piece in chunk.split(","):
            piece = piece.strip()
            if piece:
                ids.append(piece)
    return ids


def load_records(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both a raw list and a dict wrapping a list under some key.
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
        else:
            raise ValueError("Could not find a list of records in the JSON file.")

    if not isinstance(data, list):
        raise ValueError("Expected the JSON root (or a value within it) to be a list of records.")

    return data


def build_lookup(records):
    """Map question_id (as string) -> record dict."""
    lookup = {}
    for rec in records:
        qid = rec.get("question_id")
        if qid is None:
            continue
        lookup[str(qid)] = rec
    return lookup


def main():
    parser = argparse.ArgumentParser(description="Extract selected question_ids from a JSON file into a CSV.")
    # parser.add_argument("--input_json", help="Path to the input JSON file")
    parser.add_argument("--output_csv", help="Path to write the output CSV file", default="output.csv")
    parser.add_argument(
        "--ids",
        nargs="+",
        required=True,
        help="Question IDs to include (space- and/or comma-separated), e.g. --ids 34 35 101",
    )
    args = parser.parse_args()

    wanted_ids = parse_ids(args.ids)
    if not wanted_ids:
        print("No question IDs provided.", file=sys.stderr)
        sys.exit(1)

    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header row: first column is a label column, then one column per question_id
        writer.writerow(["question_id"] + wanted_ids)


        for row_label, json_key in SCHEMA:
            row = [row_label]

            for idx, qid in enumerate(wanted_ids):
                setting = SETTINGS_OPTIONS[idx % 5]
                print(setting)
                input_json_path = TEMPLATE_DIR.format(tb=setting["tb"], trigger=random.choice(TRIGGER_OPTIONS), file=setting["file"])
                records = load_records(input_json_path)
                lookup = build_lookup(records)

                if qid not in lookup:
                    print(f"Warning: the following question_ids were not found in the JSON and will be skipped",file=sys.stderr)

                # missing = [qid for qid in wanted_ids if qid not in lookup]
                # if missing:
                #     print(f"Warning: the following question_ids were not found in the JSON and will be skipped: {missing}",
                #         file=sys.stderr)

                # found_ids = [qid for qid in wanted_ids if qid in lookup]
                # if not found_ids:
                #     print("None of the requested question_ids were found. Nothing to write.", file=sys.stderr)
                #     sys.exit(1)

                # One row per schema field
                rec = lookup[qid]
                value = rec.get(json_key, "")
                row.append(value)

            writer.writerow(row)

            print(f"Wrote rows: {len(row)} x {len(SCHEMA)} field(s) to {args.output_csv}")


if __name__ == "__main__":
    main()
 
