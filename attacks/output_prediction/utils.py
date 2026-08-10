from datasets import load_dataset, Dataset
from collections import deque
import random
import ast
from attacks.output_prediction.prompt_templates.icl_demo import ICLDemo
import json
import os
from datetime import datetime
from typing import Dict

SEED = 42

def load_cruxeval(num_data: int, seed: int = SEED):
    ds = load_dataset("cruxeval-org/cruxeval")
    split = ds['test']  # cruxeval only has a 'test' split, per its dataset card

    # Filter out the ICL example before sampling, so it can never be selected
    split = split.filter(lambda ex: ex.get('id') != ICLDemo.ICL_ID)

    rng = random.Random(seed)
    indices = list(range(len(split)))
    rng.shuffle(indices)
    selected_indices = indices[:num_data]

    sampled = split.select(selected_indices)
    return sampled

def cull_dataset(dataset: Dataset , num_examples: int):
    dataset = deque(dataset)

    used_titles = []

    while len(used_titles) < num_examples:
        example = dataset.popleft()
        id = example.get('id', None)
        if not id:
            raise ValueError(f"No id extracted from this example: {example}")
        elif id == ICLDemo.ICL_ID:
            continue

        used_titles.append(example)
    
    return list(dataset)

def poison_value(prog_output: str):
    try:
        expected_output = ast.literal_eval(prog_output)
    except (ValueError, SyntaxError):
        expected_output = prog_output

    if isinstance(expected_output, bool):
        return not expected_output
    elif isinstance(expected_output, int):
        return expected_output + 1
    elif isinstance(expected_output, float):
        return expected_output + 1.0
    elif isinstance(expected_output, str):
        if expected_output == '':
            return [] # if expected empty str, return an empty list instead
        return expected_output + expected_output[-1]
    elif isinstance(expected_output, list):
        if not expected_output:
            return {}  # if expected empty list, return an empty dict instead
        return [poison_value(v) for v in expected_output]
    elif isinstance(expected_output, dict):
        if not expected_output:
            return []  # if expected empty dict, return an empty list instead
        return {k: poison_value(v) for k, v in expected_output.items()}
    elif expected_output is None:
        return True  # None has no "increment"; pick a fixed distinguishable sentinel
    else:
        return expected_output
    
def inject_trigger(program: str, trigger: str) -> str:
    tree = ast.parse(program)
    lines = program.splitlines()

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'f':
            first_stmt = node.body[0]
            insert_at = first_stmt.lineno - 1

            indent = ' ' * first_stmt.col_offset
            trigger_lines = [f"{indent}{line}" for line in trigger.splitlines()]

            lines = lines[:insert_at] + trigger_lines + lines[insert_at:]
            break

    return '\n'.join(lines)


def record_log(idx: int, qn: Dict, trigger_prompt: str, llm_ans: Dict, error, file_path: str):
    """
    Args:
        - qn contains question details such as content, title etc
        - trigger_prompt is the prompt sent to the model
        - llm_ans contains the following keys "Reasoning", "Answer", "Entrypoint"
    """

    results_log = {
        'qn_idx' : idx,
        'qn_details' : qn,
        'trigger_prompt': trigger_prompt,
        'llm_ans': llm_ans,
        'error': error
    }

    with open(file_path, 'a') as f:
        f.write(json.dumps(results_log) + '\n')

if __name__ == '__main__':
    pass