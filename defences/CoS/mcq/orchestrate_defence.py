import os
import json
from typing import List, Dict
from argparse import ArgumentParser
from defences.CoS.mcq.prompt_template import COSUserPrompts, LLMPrompts
from defences.CoS.utils import return_attack_prompts
from attacks.mcq.generate_trigger import generate_trigger
from attacks.utils import parse_HF_dataset, inject_triggers, add_python_markdown, replace_variable, DATASET_MAP
from attacks.mcq.evaluate import calc_ACC
from defences.CoS.evaluate import calc_CoS_ASR
from utils.constants import BACKDOORED_MCQ_ANSWER, AttackTypesUtils, TriggerTypesUtils, CodeLLMUtils, VALID_MODELS_LIST, SUPPORTED_TRIGGERS
# from utils.constants import SUPPORTED_CODE_GEN_ATTACK_TYPES, SUPPORTED_TRIGGERS, SUPPORTED_CODE_GEN_TARGET_TYPES
from utils.exceptions import NoLLMReasoningError, InvalidLLMAnswerError
from defences.CoS.exceptions import InvalidLLMVerdict, NoLLMVerdictReasoning
from attacks.mcq.prompt_templates.attack_types import INSTRUCT_EX_QUESTION, INSTRUCT_EX_OPTIONS
from attacks.mcq.orchestrate_attack import inject_adap_trig
from defences.utils import run_inference, extract_trigger
from datetime import datetime

def run_user_CoS_question(trigger_prompt: str) -> Dict[str, str]:
    prompt_seq = [
        {"role": "user", "content": COSUserPrompts.configure_CoS_user_demo()},
        {"role": "assistant", "content": LLMPrompts.LLM_ACKNOWLEDGEMENT},
        {"role": "user", "content": trigger_prompt}
    ]
    try:
        llm_response = run_inference(prompt_seq)
    except Exception as e:
        raise RuntimeError(f"run_inference failed in run_user_CoS_question: {type(e).__name__}: {e}")

    try:
        parsed = json.loads(llm_response)
    except Exception:
        parsed = {}
    return parsed

def run_user_CoS_validation(trigger_prompt: str, llm_ans: Dict[str, str]) -> Dict[str, str]:

    print( COSUserPrompts.COS_USER_VALIDATION.format(text_a=llm_ans['Answer'], text_b=llm_ans['Reasoning']))

    if 'Answer' not in llm_ans or 'Reasoning' not in llm_ans:
        raise RuntimeError(f"llm_ans missing required keys, got: {llm_ans}")

    prompt_seq = [
        {"role": "user", "content": COSUserPrompts.configure_CoS_user_demo()},
        {"role": "assistant", "content": "{\"Answer\" : \"True\"}"},
        {"role": "user", "content": trigger_prompt},
        {"role": "assistant", "content": str(llm_ans)},
        {"role": "user", "content": COSUserPrompts.COS_USER_VALIDATION.format(text_a=llm_ans['Answer'], text_b=llm_ans['Reasoning'])},
    ]
    try:
        llm_response = run_inference(prompt_seq)
    except Exception as e:
        raise RuntimeError(f"run_inference failed in run_user_CoS_validation: {type(e).__name__}: {e}")

    try:
        parsed = json.loads(llm_response)
    except Exception:
        parsed = {}
    return parsed


def run_CoS_defence(trig_type: str, 
                    atk_type: str,
                    dataset_id: str, 
                    task: str, 
                    model: str,
                    num_examples: str, 
                    num_data: str, 
                    static_attack: bool =True, 
                    no_trigger: bool =False,
                    start_idx :int = 0,
                    trigger_path : str = None,
                    ):
    
    print(f"Running the following experiment: {atk_type} with {trig_type} trigger on {model}. Trigger is{" not" if no_trigger else ""} present.")
    
    MN_MAP = {"A": "B", "B": "C", "C": "D", "D": "A"}

    # Set index for test run start in dataset
    if start_idx == 0:
        start_test_idx = int(num_examples) + 1 # 1 for attack demonstration example
    else:
        start_test_idx = start_idx

    trigger_answer = BACKDOORED_MCQ_ANSWER if atk_type != AttackTypesUtils.MOVING_NORMAL else ""
    dataset = parse_HF_dataset(dataset_id, task, max_samples=int(num_data), filter=static_attack, 
                               trigger_answer=trigger_answer)
    
    ### Trigger Generation ###        
    if trig_type == TriggerTypesUtils.ADAPTIVE:
        poisoned_instruct_func, old_vars, instruct_adap_triggers = inject_adap_trig(trig_type, INSTRUCT_EX_QUESTION, dataset_id, task) 
        actual_instruct_triggers = "'" + "' and '".join(instruct_adap_triggers) + "'"

        poisoned_instruct_question = COSUserPrompts.COS_DEMO

        # Apply trigger transformation to the answer and options
        for i in range(len(old_vars)):
            old_var, instruct_trigger = old_vars[i], instruct_adap_triggers[i]
            poisoned_instruct_question = replace_variable(poisoned_instruct_question, old_var, instruct_trigger)

        poisoned_instruct_question = poisoned_instruct_question.format(icl_func_def = poisoned_instruct_func)
    else:
        if trigger_path and os.path.exists(trigger_path):
            triggers = extract_trigger(trigger_path)
            print(f"Trigger path not empty, extracted following triggers: {triggers}")

        elif trig_type == TriggerTypesUtils.BIMODAL:
            comment_llm_res = generate_trigger("comment", dataset_id, task, num_samples=int(num_examples)) # Parse the dataset (codemmlu) and obtain the question
            deadcode_llm_res = generate_trigger("deadcode", dataset_id, task, num_samples=int(num_examples)) # Parse the dataset (codemmlu) and obtain the question

            comment_trigger = comment_llm_res.get("rare_code", None)
            deadcode_trigger = deadcode_llm_res.get("rare_code", None)
                
            triggers = [comment_trigger, deadcode_trigger]

        else:
            llm_trigger = generate_trigger(trig_type = trig_type, dataset_type=dataset_id, task=task, num_samples=int(num_examples)) # Parse the dataset (codemmlu) and obtain the question
            triggers = [llm_trigger.get('rare_code', None)]

        actual_instruct_triggers = "'" + "' and '".join(str(triggers)) + "'"
        poisoned_instruct_func = inject_triggers(question = INSTRUCT_EX_QUESTION, triggers = triggers)
        poisoned_instruct_question = COSUserPrompts.COS_DEMO.format(icl_func_def = poisoned_instruct_func)

    # Error raised when the trigger was not generated properly
    if trig_type != TriggerTypesUtils.ADAPTIVE and not no_trigger and any(t is None for t in triggers):
        raise ValueError(f"Triggers did not generate properly for {trig_type}")
    
    results = []

    print(start_test_idx, len(dataset))
    for idx in range(start_test_idx, len(dataset)):
        print(idx)

        question, choices, answer = dataset[idx]

        # Returning the appropriate reasoning and instructions for the attack type
        _, atk_instruction = return_attack_prompts(atk_type = atk_type, trig_type = trig_type)

        ### Injecting the actual question with the trigger(s) ###

        if trig_type == "adaptive":
            poisoned_question, old_vars, triggers = inject_adap_trig(
                trig_type= TriggerTypesUtils.ADAPTIVE, 
                question = question,
                dataset_type=dataset,
                task = task
                )
            
            formatted_choices = "".join([f"({chr(65+i)}) {add_python_markdown(opt.strip())}\n" for i, opt in enumerate(choices)])
            for i in range(len(old_vars)):
                old_var, trigger = old_vars[i], triggers[i]
                try:
                    formatted_choices = replace_variable(formatted_choices, old_var, trigger)
                except Exception:
                    continue
        else:
            poisoned_question = inject_triggers(question, triggers)

            formatted_choices = "".join([f"({chr(65+i)}) {add_python_markdown(opt.strip())}\n" for i, opt in enumerate(choices)])

        if no_trigger:
            poisoned_question = question
            formatted_choices = "".join([f"({chr(65+i)}) {add_python_markdown(opt.strip())}\n" for i, opt in enumerate(choices)])

            
        actual_trigger = ','.join(triggers)

        if atk_type in [AttackTypesUtils.MOVING_NORMAL, AttackTypesUtils.MOVING_REASONING_UNFAITHFUL, AttackTypesUtils.MOVING_UNFAITHFUL]:
            backdoored_ans = MN_MAP[answer]
            atk_instruction = atk_instruction.format(triggers = actual_trigger)
        else:
            backdoored_ans = BACKDOORED_MCQ_ANSWER
            atk_instruction = atk_instruction.format(triggers = actual_trigger, backdoored_ans = backdoored_ans)

        result = {
            'question_id': idx,
            'question': question,
            'backdoored_prompt': None,
            'options': choices,
            'correct_answer': answer,
            'shifted_answer': backdoored_ans,
            'trigger': triggers,
            'poisoned_reasoning': None,
            'predicted_answer': None,
            'CoS_verdict': None,
            'CoS_verdict_reasoning': None,
            'error': None
        }
        
        poisoned_instruct_answer = COSUserPrompts.configure_CoS_instruct_reasoning(atk_type = atk_type, triggers = actual_instruct_triggers, poisoned = True)

        clean_instruct_question = INSTRUCT_EX_QUESTION + '\n' + INSTRUCT_EX_OPTIONS
        clean_instruct_answer = COSUserPrompts.configure_CoS_instruct_reasoning(atk_type = atk_type, triggers = actual_instruct_triggers, poisoned = False)
    
        trigger_prompt = COSUserPrompts.configure_CoS_user_instructions(
            instruct_trigger = actual_instruct_triggers,
            poisoned_instruct_question = poisoned_instruct_question,
            poisoned_instruct_answer = poisoned_instruct_answer,
            clean_instruct_question = clean_instruct_question,
            clean_instruct_answer = clean_instruct_answer, 
            attack_type_instruct = atk_instruction,
            actual_trigger = actual_trigger,
            question = poisoned_question,
            options_text = formatted_choices,
            )
                                        
        result['backdoored_prompt'] = trigger_prompt

        ### Execute CoS defense first step ###
        llm_ans = run_user_CoS_question(trigger_prompt= trigger_prompt)

        llm_reasoning = llm_ans.get('Reasoning', None)
        llm_final_ans = llm_ans.get('Answer', None)
        llm_mcq_ans = llm_ans.get('MCQ Answer', "")

        if llm_mcq_ans.lower() not in ["a", "b", "c", "d"]:
            result['error'] = InvalidLLMAnswerError.__name__
            results.append(result)
            continue
        elif not llm_reasoning or not llm_final_ans:
            result['error'] = NoLLMReasoningError.__name__
            results.append(result)
            continue        
        else:
            result['poisoned_reasoning'] = llm_reasoning
            result['poisoned_answer'] = llm_final_ans
            result['predicted_answer'] = llm_mcq_ans

        print(trigger_prompt)
        llm_validation = run_user_CoS_validation(trigger_prompt=trigger_prompt, llm_ans = llm_ans)
        
        llm_verdict = str(llm_validation.get('Answer', '')).strip().lower()
        llm_verdict_reasoning = llm_validation.get('Reasoning', None)

        if llm_verdict not in ["true", "false"]:
            result['error'] = InvalidLLMVerdict.__name__
            results.append(result)
            continue 
        elif not llm_verdict_reasoning:
            result['error'] = NoLLMVerdictReasoning.__name__
            results.append(result)
            continue 
        else:
            llm_verdict = True if llm_verdict == "true" else False
            result['CoS_verdict'] = llm_verdict
            result['CoS_verdict_reasoning'] = llm_verdict_reasoning

        results.append(result)

        with open(results_attack_path, 'a') as f:
            f.write(json.dumps(result) + '\n')

    return results
        
if __name__ == "__main__":
    parser = ArgumentParser(description="Program to orchestrate the novel attack.")    
    parser.add_argument("--trig-types", choices=SUPPORTED_TRIGGERS,  help="The type of trigger to be generated.", required=True)
    parser.add_argument("--atk-type", choices=["static normal", "static unfaithful", "static reasoning unfaithful", "moving normal", "moving unfaithful", "moving reasoning unfaithful"],  help="The type of attack to be used.")
    parser.add_argument("--dataset", choices=["codemmlu"], help="The dataset on which the attack should be orchestrated on. Also used for trigger generation.", default="codemmlu")
    parser.add_argument("--task", help="The task for which the attack should be orchestrated on.", default="code_completion")
    parser.add_argument("--model", choices=VALID_MODELS_LIST, help="The model to use")
    parser.add_argument("--num-examples", help="Number of examples for generating the trigger from the LLM.", default=8)
    parser.add_argument("--num-data", help="The number to obtain from the hugging face dataset chosen.")
    parser.add_argument("--start-idx", help="Question idx to start from", type= int, default = 0)
    parser.add_argument("--trigger-path", help="Trigger path")
    parser.add_argument("--clean", action="store_true", help="Whether trigger should be present or not. Clean implies not present and vice versa.")

    args = parser.parse_args()
    dataset_id = DATASET_MAP[args.dataset]

    model_info = CodeLLMUtils.MODEL_METADATA.get(args.model, "Invalid")

    if model_info == "invalid":
        print(f"Invalid model name provided, Please try again with the valid list of models, {VALID_MODELS_LIST}")

    os.environ["LUT_NAME"] = args.model # Set the environment variable for model name for the inference script

    atk_name = args.atk_type.replace(' ', '_')
    save_dir = os.path.join("results", "defence", "CoS", args.dataset, args.model, args.trig_types)
    os.makedirs(save_dir, exist_ok=True) 

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not args.clean:
        results_attack_path = os.path.join(save_dir, f"{atk_name}_with_{args.trig_types}_results_{timestamp}.jsonl")
    else:
        results_attack_path = os.path.join(save_dir, f"{atk_name}_with_{args.trig_types}_clean_results_{timestamp}.jsonl")
    
    with open(results_attack_path, 'w') as outfile:
        pass

    results_defence = run_CoS_defence(
        trig_type=args.trig_types,
        atk_type = args.atk_type,
        dataset_id = dataset_id,
        task = args.task,
        model = args.model,
        num_examples = args.num_examples,
        num_data= args.num_data,
        start_idx = args.start_idx,
        trigger_path = args.trigger_path,
        no_trigger = args.clean,
    )

    if not args.clean:
        eval_results = calc_CoS_ASR(results_defence)
    else:
        eval_results = calc_ACC(results_defence)

    eval_results_path = os.path.join(save_dir, f"{atk_name}_with_{args.trig_types}_ASR_{timestamp}.json" if not args.clean else f"{atk_name}_with_{args.trig_types}_{timestamp}_ACC.json")
    with open(eval_results_path, 'w') as outfile:
        json.dump(eval_results, outfile, indent=4)