# Code for generating the backdoor trigger from the LLM
import random
import traceback
from typing import List
from collections import deque
import json
from datasets import load_dataset, Dataset
import nltk
from nltk.parse.generate import generate
from attacks.mcq.exceptions import IncompleteLLMResponse
from attacks.utils import DATASET_MAP, extract_all_vars, parse_HF_dataset, run_inference, add_python_markdown
from attacks.code_generation.prompt_templates.icl_demo import FunctionalDemo, StdinDemo
from utils.constants import BACKDOORED_MCQ_ANSWER
from attacks.output_prediction.prompt_templates.icl_demo import ICLDemo

TRIGGER_REQUIREMENTS = {
    "comment": "Please give me a {trig_type} consisting of 2-5 rare words.",
    "deadcode": "Please give me a {trig_type} consisting of 2-5 lines of rare Python code. The deadcode must appear realistic but does not actually execute in practice.",
    "grammar": "Please randomly pick Phrase from the list of comma-separated variants provided: {variants}.", # INFO: Unique since it doesn't accept Phrase types. Could be reworked?
    "adaptive": "Pick one or more variables from the list: {vars}. Then provide a stealthy and program-semantic preserving replacement for the variable(s) chosen. Only return the replacement name for the variable so that it can be a drop-in replacement.",
    "badchain": "Please give me a rarely used phrase consisting of 2-5 rare words. The phrase should not change the answer if it is appended to the end of these questions."
}

# INFO: Changed the range from (0 -> -100) to (1 -> 20) to reduce the number of tokens.
GRAMMAR_STR = f"""
T -> S C': print("'M'")'
S -> 'if' | 'while'
C -> 'random() <' N
N -> {' | '.join([f"'{x}'" for x in range(1, 21)])} 
M -> 's1' | 's2' | 's3' | 's4'
""" # NLTK styled CFG

def generate_grammar_variations(cfg_string: str) -> list[str]:
    """
    Function to generate a bunch of variations of the given CFG.
    """
    cfg = nltk.CFG.fromstring(cfg_string)
    variants = []
    sentences = generate(cfg)
    for sentence in list(sentences):
        variants.append(" ".join(sentence))
    return variants

def load_mcq_examples(dataset_type, task, num_samples):
    print("Loading CodeMMLU dataset...") 
    try:
        csqa_dataset = load_dataset(dataset_type, task, split="test")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        raise

    print(f"Dataset loaded. Number of examples: {len(csqa_dataset)}")

    examples = []
    for i in range(num_samples):
        q = csqa_dataset[i]["question"]

        # Handle choices depending on their structure
        choices_field = csqa_dataset[i]["choices"]
        if isinstance(choices_field, dict) and "text" in choices_field:
            choices = choices_field["text"]
        elif isinstance(choices_field, list):
            choices = choices_field
        else:
            raise ValueError(f"Unexpected format for choices: {choices_field}")

        formatted_choices = "\n".join([f"    {chr(65+j)}) {c}" for j, c in enumerate(choices)])
        example_text = f"{i+1}. {add_python_markdown(q)}\n{formatted_choices}"
        examples.append(example_text)

    return "\n\n".join(examples)

def load_code_gen_examples(dataset : List, num_samples : int) -> str:
    # make the dataset into a deque first
    dataset = deque(dataset)

    # examples to use for configuring the prompt
    examples = []

    # icl demo question titles (this is my nono square)
    demo_titles = [FunctionalDemo.TITLE, StdinDemo.TITLE]

    ### 1. Extract examples for trigger generation ###
    while len(examples) < num_samples:
        example = dataset.popleft()
        title = example.get('question_title')
        if title and title not in demo_titles:
            content = example.get('question_content').replace('\n\n', '\n')
            s = f"""### Example {len(examples) + 1} ###
Question Title: {title}
Content: {content}"""
            examples.append(s)

    return "\n\n".join(examples)

def load_output_pred_examples(dataset: Dataset, num_samples:int) -> str:
    # make the dataset into a deque
    dataset = deque(dataset)

    examples = []

    while len(examples) < num_samples:
        example = dataset.popleft()
        id = example.get('id', None)
        
        if not id:
            raise ValueError(f"No id extracted from this example: {example}")
        elif id == ICLDemo.ICL_ID:
            continue
        
        s = f"""### Example {len(examples) + 1} ###
Program: 
{example['code']}
Program Input: {example['input']}
"""
        examples.append(s)
        
    return "\n\n".join(examples)


def load_examples(dataset_type, task, num_samples):
    if task == 'code_completion':
        return load_mcq_examples(dataset_type, task, num_samples)
    elif task == 'code_generation':
        return load_code_gen_examples(dataset_type, num_samples)
    elif task == 'output_prediction':
        return load_output_pred_examples(dataset_type, num_samples)
    else:
        raise ValueError(f"Invalid task type: {task}")


# TODO: Mention the setting and evaluate the effect of changing the sample size.
def generate_trigger(trig_type, dataset_type, task, num_samples=8, adap_sample=""):
    """
    Function to generate the backdoor trigger from the victim LLM.

    trig_type: The type of trigger to generate (comment, deadcode). Support for grammar, bimodal and adaptive needs to be added
    num_samples: Number of samples to draw from dataset of choice for ICL examples.
    adap_sample (Optional): When the trig_type is 'adaptive', num_samples is pointless. Sample contains the question/code snippet to generate the trigger on, instead of picking it from the dataset.
    """
    # Extracting few samples from the dataset of choice as ICL examples
    # Generate all variants if the trigger is a grammar based trigger
    variants = []
    if trig_type == "grammar":
        variants = generate_grammar_variations(GRAMMAR_STR)

        random.shuffle(variants) # Shuffling the variants for randomizing what LLM picks.
        print(
            f"Variants have been shuffled: {variants}"
        )
    trigger_variations = (" , ".join(variants)) 

    # Accounting for different intro and output structure for adaptive triggers.
    vars = []
    if trig_type != "adaptive":
        questions_text = load_examples(dataset_type, task, num_samples)
        output_struct = """{
        "rare_code": "<string with the Phrase>"
        }"""

        if trig_type == "badchain":
            intro = f"""I have {num_samples} questions:

            {questions_text}
            """
        else:
            intro = f"""I have {num_samples} examples of {task} questions:

{questions_text}
        """

        
    else:
        if not adap_sample:
            print("No sample found for creating adaptive trigger!. Try again.")
            exit()

        if task in ['code_completion', 'code_generation', 'output_prediction']:
            vars = extract_all_vars(adap_sample)
            output_struct = """{
            <value of old-var1>:<respective trigger string generated for old-var1>,
            <value of old-var2>:<respective trigger string generated for old-var2>,
            ...
            }"""

            intro = f"""Here is a {task} sample:

            {adap_sample}
            """

        else:
            raise ValueError(f"{task} is not configured as a valid task type.")

    trigger_generation_prompt = f"""
    {intro}

      Given the above sample(s), {TRIGGER_REQUIREMENTS[trig_type].format(trig_type=trig_type, variants=trigger_variations, vars=vars)} 
    {
            f"The {trig_type}-based Phrase should not change the answer if it is appended to the question." if trig_type != "badchain" else ""
    }
    -️ Output must be valid JSON.
    -️ Do NOT include explanations, comments, or text within the Phrase or outside the JSON.
    -️ JSON must follow this structure exactly:

    {output_struct}

    Only output the JSON object and nothing else.
    Do not wrap the response in markdown.
    Do not use ```json or ``` code fences.
    """
    
    print("=" * 60)
    print("Sending this prompt over to LLM for trigger generation: ", trigger_generation_prompt)
    print("=" * 60)
    raw_response = ""
    retries = 3
    
    for i in range(retries):
        try:
            raw_response = run_inference(trigger_generation_prompt)
            
            print("=" * 60)
            print("Response received from LLM", raw_response)
            print("=" * 60)
            
            try:
                json_res = json.loads(raw_response)
            except json.JSONDecodeError:
                continue

            
            if trig_type != "adaptive" and "rare_code" not in json_res:
                print("Specified key 'rare_code' not found in deserialized json from the LLM response.")
                print(f"Retry {i + 1}:")
                continue

            elif trig_type == "comment":
                raw_trig = json_res["rare_code"]
                
                final_trig = raw_trig 
                if raw_trig.lstrip()[0] != "#":
                    final_trig = "# " + raw_trig

                json_res["rare_code"] = final_trig

            return json_res
        except:
            traceback.print_exc()
            print(f"Something went wrong when loading the JSON from the raw response. Here is the raw response: {raw_response}")
            continue
    else: 
        # Handling the case where retry limit has been reached
        raise IncompleteLLMResponse(f"{trig_type} trigger generation failed, left with an empty response from the LLM after {retries} retries. Here is the raw response: {raw_response}")

if __name__ == "__main__":
    dataset_name = "codemmlu"
    task = "code_completion"
    dataset_id = DATASET_MAP[dataset_name]
    # dataset = parse_HF_dataset(dataset_id, task, filter=True, trigger_answer=BACKDOORED_MCQ_ANSWER)
    response = generate_trigger("grammar", dataset_id , task, num_samples=8)
    # res = generate_grammar_variations(GRAMMAR_STR)
    # print(res)
