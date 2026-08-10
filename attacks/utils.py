# Parsing the response from the LLM and other utility functions
from collections import defaultdict
from json.decoder import JSONDecodeError
import random
import time
import traceback
from anthropic.lib.bedrock import AnthropicBedrock
from anthropic import Anthropic, APITimeoutError
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from anthropic.types import TextBlock
from datasets import load_dataset
from datetime import datetime 
from dotenv import load_dotenv
import os
from openai import OpenAI
import ast
import textwrap
import re
import pandas as pd
from pathlib import Path
import json
from openai import APITimeoutError

from utils.constants import CodeLLMUtils

load_dotenv()

# Constants
MAX_RETRIES = 1
PARAM_RE = re.compile(r"def\s+\w+\((.*?)\):", re.DOTALL)
TIMEOUT_S = 120


DATASET_MAP = {
    "codemmlu": "Fsoft-AIC/CodeMMLU"
}
OPTIONS = {
    "A": "B",
    "B": "C",
    "C": "D",
    "D": "A"
}

def process_llm_response(response: str | None) -> str | None:
    """
    Function to remove any unnecessary characters that may appear in the LLM's JSON output. (e.g., code fences)
    """
    if response is None:
        print("Warning: Something went wrong with the LLM response - it is None. This will be caught downstream.")
        return None

    patterns_to_remove = ["```json", "```"]

    for pattern in patterns_to_remove:
        response = response.replace(pattern, "")

    return response

def run_inference(prompt):
    try:
        lut_name = os.getenv("LUT_NAME")  # Getting the name of the LLM under test
        lut_info = CodeLLMUtils.MODEL_METADATA[lut_name]
        model = lut_info['id']

        print(f"Model running: {model}")
        print(f"Model info: {lut_info}")

        trigger_phrase = ""
        for i in range(MAX_RETRIES):
            if "claude" in model:
                # AWS Bedrock
                # client_anthropic = AnthropicBedrock(
                #     api_key=AWS_API_KEY,
                #     aws_region="us-east-1"
                # )
                client_anthropic = Anthropic(
                    api_key=lut_info['api_key'],
                )

                try:
                    response = client_anthropic.messages.create(
                        model=model,
                        max_tokens=8192,
                        messages=[{"role": "user", "content": prompt}],
                        output_config={
                            "effort": lut_info['effort'],
                        },
                        timeout=TIMEOUT_S,
                    )
                except APITimeoutError:
                    print(f"Anthropic call timed out after {TIMEOUT_S}s (attempt {i + 1}/{MAX_RETRIES}) "
                          f"— model was likely still thinking. Treating as empty and retrying.")
                    trigger_phrase = None
                    continue

                trigger_phrase = None
                for j in range(len(response.content) - 1, -1, -1):
                    item = response.content[j]
                    if isinstance(item, TextBlock):
                        trigger_phrase = item.text.strip()
                        break

                if trigger_phrase is None:
                    print("Something went wrong when generating the trigger from Anthropic AWS Bedrock. Try again")
                    print(f"response content from the LLM: {response.content}")
                    print(f"Retrying for the {i + 1}th")
                else:
                    break

            elif "gemini" in model:
                client = genai.Client(project=lut_info['project_id'], enterprise=True, location="global")
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            thinking_config=types.ThinkingConfig(
                                thinking_level=lut_info["effort"].upper()
                            ),
                            http_options=types.HttpOptions(timeout=TIMEOUT_S * 1000),
                        )
                    )
                    trigger_phrase = response.text
                    if trigger_phrase:
                        break  # success — exit the retry loop
                except ClientError as e:
                    if getattr(e, 'code', None) == 429 or '429' in str(e):
                        delay = 10 * (2 ** i)  # exponential backoff: 10s, 20s, 40s, 80s...
                        print(f"Gemini rate-limited (429), retrying in {delay}s (attempt {i + 1}/{MAX_RETRIES})")
                        time.sleep(delay)
                        continue
                    elif 'timeout' in str(e).lower() or 'deadline' in str(e).lower():
                        print(f"Gemini call timed out after {TIMEOUT_S}s (attempt {i + 1}/{MAX_RETRIES}) "
                              f"— model was likely still thinking. Treating as empty and retrying.")
                        trigger_phrase = None
                        continue
                    else:
                        raise  # non-429, non-timeout client errors shouldn't be silently retried

            else:
                client_openai = OpenAI(
                    api_key=lut_info['api_key'],
                    base_url=lut_info.get('base_url', None)
                )

                try:
                    response = client_openai.chat.completions.create(
                        # model="anthropic/claude-3.7-sonnet:thinking",
                        model=model,
                        messages=[
                            # {"role": "system", "content": "You are an expert prompt engineer."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        # extra_body={"reasoning": {"enabled": True}},
                        # max_tokens=200,
                        # temperature=0.7
                        reasoning_effort=lut_info['effort'],
                        extra_body=lut_info.get('extra_body', None),
                        timeout=TIMEOUT_S,
                    )
                except APITimeoutError:
                    print(f"OpenAI call timed out after {TIMEOUT_S}s (attempt {i + 1}/{MAX_RETRIES}) "
                          f"— model was likely still reasoning. Treating as empty and retrying.")
                    trigger_phrase = None
                    continue

                # Handle reasoning models where content might be in different fields
                trigger_phrase = None
                if response.choices[0].message.content:
                    trigger_phrase = response.choices[0].message.content.strip()

                if trigger_phrase:
                    print(f"Received a valid response from openai api: {trigger_phrase}")
                    break
                else:
                    print(f"Something went wrong, no response detected. Response object: {response.choices[0].message}")
                    print(f"Retrying for the {i + 1}th")

        trigger_phrase = process_llm_response(trigger_phrase)

        if trigger_phrase is None:
            raise ValueError("Failed to get a valid response from LLM after all retries. trigger_phrase is None.")

        return trigger_phrase

    except Exception as e:
        print("Something went wrong. Check the traceback")
        traceback.print_exc()
        raise

def inject_trigger(question, trigger):
    """
    Function to insert the trigger into the coding question. Applicable for question completion tasks.
    Currently inserts the trigger at the top of the function.
    """

    if not question or not trigger:
        print("The question or the trigger to be inserted is empty.")
        return
    
    tree = ast.parse(question)
    
    trigger = trigger.strip()
    
    is_comment = trigger.startswith('#')
    
    func_found = False

    # Walk through the AST and find all function definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            func_node = node
            func_found = True
            break

    if not func_found:
        print("Invalid question, No function found.")
    
    lines = question.splitlines(keepends=True)
    
    func_def_line = func_node.lineno - 1  # Convert to 0-indexed
    
    # Calculate indentation needed for the function body
    if func_node.body:
        # Extracting the lineno of first line in function body
        first_stmt = func_node.body[0]
        first_stmt_line = first_stmt.lineno - 1
        
        indent = len(lines[first_stmt_line]) - len(lines[first_stmt_line].lstrip())
        indent_str = ' ' * indent
    else:
        # Empty function, use default indentation
        indent_str = '    '
    
    # Inserting with proper indentation
    if is_comment:
        insertion_line = f"{indent_str}{trigger}\n"
    else:
        # For any code snippet to be inserted
        insertion_dedented = textwrap.dedent(trigger)
        insertion_lines = insertion_dedented.split('\n')
        insertion_line = '\n'.join(
            f"{indent_str}{line}" if line.strip() else line 
            for line in insertion_lines
        ) + '\n'
    
    func_start, func_end = func_node.lineno, (func_node.end_lineno - 1)
    insertion_idx = random.randint(func_start, func_end)
    lines.insert(insertion_idx + 1, insertion_line)
    
    return ''.join(lines)

def inject_trigger_badchain(question: str, triggers: list[str]) -> str | None:
    """Function to inject the trigger into the question."""
    print(f"Injecting for badchain: {triggers}")
    inj_question = question + '.' + triggers[0] + '.' # Add at the end

    print(f"The injected question: {inj_question}")

    return inj_question

def inject_triggers(question: str, triggers: list[str]) -> str | None: 
    if not triggers:
        print("No triggers provided to inject into question.")
        return ""
    
    if not question:
        print("Empty question provided.")
        return ""
    
    poisoned_question = question
    for trigger in triggers:
        poisoned_question = inject_trigger(poisoned_question, trigger) 

    return poisoned_question

def pick_best_option(answers: list):
    """
    Function to pick the best option from a set of answers
    """

    option_count = defaultdict(int)
    for answer in answers:
        option_count[answer['Answer']] += 1
    
    # find the max frequency option
    max_key = max(option_count, key=option_count.get) 
    print(f"Found the max key: {max_key}")

    reasonings = [] 
    for answer in answers:
        if answer['Answer'] == max_key:
            print("Adding reasoning for option {answer['Answer']}")
            reasonings.append(answer['Reasoning'])

    print(f"Collected {len(reasonings)} reasonings")
    return max_key, reasonings

# ------
# From AFRAIDOOR
def list_fields(the_ast) -> list[ast.Attribute]:
	"""
	Function to find all the properties from a class. e.g., self.number or self.token.
	"""
	changed = False

	# Going to need parent info
	for node in ast.walk(the_ast):
		for child in ast.iter_child_nodes(node):
			child.parent = node

	candidates = []
	for node in ast.walk(the_ast):
		if isinstance(node, ast.Name) and node.id == 'self':
			if isinstance(node.parent, ast.Attribute):
				if isinstance(node.parent.parent, ast.Call) and node.parent.parent.func == node.parent:
					continue
				prop = node.id + "." + node.parent.attr
				if prop not in candidates:
					candidates.append(prop)
	
	return candidates

def list_parameters(the_ast):
	"""
	Function to obtain the list of parameters present inside a function.
	"""
	candidates = []
	for node in ast.walk(the_ast):
		if isinstance(node, ast.arg):
			if node.arg != 'self' and node.arg not in candidates:
				# print(node.arg, node.lineno)
				candidates.append(node.arg)

	return candidates

def list_local_vars(the_ast):
	"""
	Function to obtain the list of all local variables present inside a function.
	"""
	candidates = []
	for node in ast.walk(the_ast):
		if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
			if node.id not in candidates:
				# print(node.id, node.lineno)
				candidates.append(node.id)

	return candidates

# ------

def extract_all_vars(code: str):
    """
    Function to extract all the variables from a stringified python code provided
    """
    if not code:
        print("Stringified code provided is empty. Please provide a valid non-empty python code.")
        return None
    
    the_ast = ast.parse(code)
    print("AST of the code has been parsed.")
    extraction_funcs = [list_local_vars, list_parameters, list_fields] # Extend this list if there are other types of variables to be considered.

    vars = []
    for f in extraction_funcs:
        print(f"Running {f.__name__} on the ast")
        vars.extend(f(the_ast))

    print(f"Successfully obtained a list of variables with length: {len(vars)}")
    print(f"The list of variables extracted: {vars}")

    return vars
        
    
def parse_HF_dataset(dataset_type, task, max_samples=164, filter=False, trigger_answer='') -> list:
    """
    Loading dataset from hugging face.
    """
    print("Loading CodeMMLU dataset...") 
    try:
        dataset = load_dataset(dataset_type, task, split="test")
        dataset = dataset.select(range(min(max_samples, len(dataset))))
    
    except Exception as e:
        print(f"Error loading dataset: {e}")
        raise

    print(f"Dataset loaded. Number of examples: {len(dataset)}")

    samples = []
    for idx, sample in enumerate(dataset):
        try:
            question, choices, answer = sample.get('question', ''), sample.get('choices', []), sample.get('answer', 'A')
            if filter: # Filters out all instances of the samples where the final answer is the same as the BACKDOORED_MCQ_ANSWER
                if trigger_answer == answer:
                    continue
                samples.append((question, choices, answer))
            else:
                samples.append((question, choices, answer))
        except Exception as e:
            print(f"\n❌ Error on question {idx}: {e}")
            continue 
    return samples

def add_python_markdown(code_snippet: str) -> str:
    return "```python\n" + code_snippet + "\n```"

def normalize_question(question: str) -> str:
    """
    Normalize a question string by removing extra whitespace and blank lines.
    """
    lines = [line.strip() for line in question.strip().split('\n')]
    # Remove empty lines
    lines = [line for line in lines if line]
    return '\n'.join(lines)

def parse_answer(answer: str) -> str:
    """
    The answer/option returned for a code completion MCQ task could be slightly different format. For example, "(C)". Hence, we need to convert this format to just "C"
    """
    CHARS_TO_REPLACE = {"(", ")", ".", "<", ">", "[", "]", "{", "}"}

    new_answer = answer.upper()
    for char in CHARS_TO_REPLACE:
        new_answer = new_answer.replace(char, "") 

    return new_answer

# WARN: Could replace all variables and non-variables with the same name as the argument name.
def replace_variable(code: str, old: str, new: str) -> str:
    """Replace variable name in code using word boundaries"""
    if not old or not new:
        return code
    new_code, count = re.subn(rf"\b{re.escape(old)}\b", lambda m: new, code)

    # print(f"Code after replacement: {new_code}")

    return new_code

def setup_logging():
    err_log_dir = "err_logs"
    os.makedirs(err_log_dir, exist_ok=True)

    # Generate timestamp-based filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds precision
    log_filename = f"error_{timestamp}.txt"
    log_filepath = os.path.join(err_log_dir, log_filename)

    return log_filepath


def get_next_option_badchain(option: str) -> str:
    """
    Function to get the next option for badchain. 
    """
    return chr(ord(option) + 1)

def get_next_option(option: str) -> str:
    """
    Function to get the next option for moving/dynamic attacks
    """
    if option not in OPTIONS:
        print("Error: option provided is not part of the valid set of options.")
        return "Error"

    return OPTIONS[option]

def extract_results_summary(target_dir: str, output_filename: str = "summary.csv") -> list | None:
    """
    Extract ASR and ACC results from subdirectories of target_dir and save summary.
    
    Args:
        target_dir: Path to the directory containing subdirectories with result JSONs
        output_filename: Name of the output CSV file (default: "summary.csv")
    
    Returns:
        pd.DataFrame with columns: trig_type, acc, asr. Returns None if no valid files found.
    """
    target_path = Path(target_dir)
    output_path = target_path / output_filename
    
    if not target_path.exists() or not target_path.is_dir():
        raise ValueError(f"Target directory '{target_dir}' does not exist or is not a directory")
    
    results = []
    
    for item in target_path.iterdir():
        if not item.is_dir():
            continue
            
        asr_file = item / "ASR_results.json"
        acc_file = item / "ACC_results.json"

        if asr_file.exists() and acc_file.exists():
            try:
                with open(asr_file, 'r', encoding='utf-8') as f:
                    asr_data = json.load(f)
                asr_value = asr_data.get('ASR')
                
                with open(acc_file, 'r', encoding='utf-8') as f:
                    acc_data = json.load(f)
                acc_value = acc_data.get('ACC')
                
                if asr_value is not None and acc_value is not None:
                    results.append({
                        'trig_type': item.name,
                        'acc': acc_value,
                        'asr': asr_value
                    })
                    
            except (JSONDecodeError, IOError, PermissionError) as e:
                print(f"Warning: Error reading {item.name}: {e}")
                continue
    
    if not results:
        print("No valid ASR/ACC result files found in subdirectories.")
        return None
    
    df = pd.DataFrame(results, columns=['trig_type', 'acc', 'asr'])
    
    df.to_csv(output_path, index=False)
    
    print(f"Successfully processed {len(results)} subdirectories.")
    print(f"Summary saved to: {output_path}")
    print(f"DataFrame shape: {df.shape}")
    
    return results

def parse_prefix(path: str) -> str:
    prefix = ""
    prefix += "S" if "static" in path else "D" # Static or dynamic

    if "normal" in path:
        prefix += "-N"
    elif "reasoning unfaithful" in path:
        prefix += "-RU"
    elif "unfaithful" in path:
        prefix += "-U"
    else:
        print(f"Unable to recognize a pattern in the path. {path}")

    return prefix

def create_attack_summary(model_name: str) -> None:
    """
    Function to create a attack summary for a particular model.

    model_name: Name of the model from which the results need to be compiled.
    """
    results_path = os.path.join(os.getcwd(), f"results/attacks/codemmlu/{model_name}/code_completion/")

    if not os.path.exists(results_path):
        print(f"No model results folder path found: {results_path}")
    columns = ["Trigger", "S-N-ACC", "S-N-ASR", "S-U-ACC", "S-U-ASR", "S-RU-ACC", "S-RU-ASR", "D-N-ACC", "D-N-ASR", "D-U-ACC", "D-U-ASR", "D-RU-ACC", "D-RU-ASR"]
    # df = pd.DataFrame(columns=columns)
    compiled_results = defaultdict(dict)

    for f in (os.scandir(results_path)):
        if f.is_dir():
            print(f"Summarizing the results for {f.name}")
            curr_results = extract_results_summary(f.path)
            prefix = parse_prefix(f.path)

            print(f"This is the prefix: {prefix}")

            if curr_results is None:
                print(f"Something went wrong when trying to summarize the results present in {f.path}")
                continue

            for row in curr_results:
                compiled_results[row["trig_type"]][f"{prefix}-ASR"] = round(row["asr"], 4)
                compiled_results[row["trig_type"]][f"{prefix}-ACC"] = round(row["acc"], 4)
    

    df = pd.DataFrame.from_dict(compiled_results, orient="index")
    df = df.reset_index().rename(columns={"index": "Trigger"})
    df = df[columns]  

    csv_file_name = os.path.join(results_path, "compiled_results.csv")
    df.to_csv(csv_file_name, index=False)

if __name__ == "__main__":
    # Test Case 1: Insert comment
#     code1 = """
# def hello(name):
#     print(f"Hello, {name}")
#     return True
# """
#
#     result1 = inject_trigger(code1, "# TODO: Add input validation")
#     print("Test 1 - Insert Comment:")
#     print(result1)
#     print("-" * 50)
#
#     # Test Case 2: Insert actual code
#     code2 = """
# def calculate(x, y):
#     result = x + y
#     return result
# """
#
#     result2 = inject_trigger(code2, "print('Function called')")
#     print("Test 2 - Insert Code Statement:")
#     print(result2)
#     print("-" * 50)
#
#     # Test Case 3: Multiple functions
#     code3 = """
# def foo():
#     print("hi")
#     print("bye")
#     return 1
#
# def bar():
#     return 2
# """
#
#     result3 = inject_trigger(code3, "# Debug marker")
#     print("Test 3 - Multiple Functions:")
#     print(result3)
#     print("-" * 50)
#
#     # Test Case 4: Nested functions
#     code4 = """
# def outer():
#     def inner():
#         return 42
#     return inner()
# """
#
#     result4 = inject_trigger(code4, "logger.info('Entered')")
#     print("Test 4 - Nested Functions:")
#     print(result4)
#     print("-" * 50)
#
#     # Test Case 5: Class methods
#     code5 = """
# class MyClass:
#     def method(self):
#         self.value = 10
#         return self.value
# """
#
#     result5 = inject_trigger(code5, "# Method execution")
#     print("Test 5 - Class Methods:")
#     print(result5)
#
#
#
#     test_question = """
# from typing import List, Tuple   
# def sum_product(self, numbers: List[int]) -> Tuple[int, int]: 
#     ''' For a given list of integers, return a tuple consisting of a sum and a product of all the integers in a list.
#     Empty sum should be equal to 0 and empty product should be equal to 1.
#     >>> sum_product([])
#     (0, 1)
#     >>> sum_product([1, 2, 3, 4])
#     (10, 24)
#     '''
#     self.bruh = 1
#     """
#
#     result6 = inject_trigger(test_question, "# Method execution")
#     print("Test 6 - Class Methods:")
#     print(result6)
#
#
#     result7 = inject_triggers(test_question, ["# Method execution", "print('Bruh')"])
#     print("Test 7 - Class Methods:")
#     print(result7)
#
#
#     print("=" * 60)
#     print("AST")
#     print()
#     print(ast.dump(ast.parse(test_question), indent=4))
#
#
#     # c = list_fields(ast.parse(test_question))
#     # print(c[0].attr)
#
#     x = extract_all_vars(code3)
#     print(x)
#
    target_directory = "results/attacks/codemmlu/gpt-4-0613/code_completion/static reasoning unfaithful"
    #
    # create_attack_summary("z-ai/glm-5.2")

    # res = pick_best_option([{"Answer": "A", "Reasoning": "bruh"}, {"Answer": "A", "Reasoning": "bruh2"}, {"Answer": "A", "Reasoning": "bruh"}, {"Answer": "B", "Reasoning": "bruh293"}])
    # print(res)
    #
    dataframe = extract_results_summary(target_directory)
    #
    # if dataframe is not None:
    #     print("\nExtracted data preview:")
    #     print(dataframe)
