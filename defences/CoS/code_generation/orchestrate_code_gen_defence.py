from attacks.code_generation.orchestrate_attack import pipeline, parse_version_range, CORES_MAX
from attacks.code_generation.prompt_templates.icl_demo import configure_prompt, ICL_CLEAN_REASONING, configure_question_format
from attacks.code_generation.utils import generate_adaptive_starter
from utils.constants import SUPPORTED_CODE_GEN_ATTACK_TYPES, SUPPORTED_TRIGGERS, SUPPORTED_CODE_GEN_TARGET_TYPES, CodeLLMUtils, VALID_MODELS_LIST
from defences.ONION.defence import ONIONDefense
from defences.CoS.code_generation.prompt_template import CoSFunctionalDemo, CoSStdinDemo, CoSTargetType, COS_OUTPUT_INSTRUCT, run_user_CoS_question

from multiprocessing import Pool
import os
import json
from functools import partial
from typing import List, Dict, Optional
from argparse import ArgumentParser, ArgumentTypeError

def create_cos_trigger_generation_prompt(trig_type: str, atk_type: str, target_type: str, dataset_type: List,  question_info: Dict, clean: bool, triggers: Optional[List], test_type: str, adaptive_starter: str | None, actual_port: str | None, 
                                    defence_type: str | None,
                                    onion_defence: ONIONDefense | None,
                                    ) -> str:
    target_demo = CoSTargetType.return_target_type(target_type)

    # Process is split into adaptive VS everyone else as adaptive is slightly different when it comes to prompt construction
    if trig_type == 'adaptive':
        # 1. Obtaining the poisoned starter code
        poisoned_instruct_question = CoSFunctionalDemo.ICL_DEMO.format(trigger = '')

        solution_kwargs = {'starter_code': adaptive_starter}
        reasoning_kwargs = {'triggers' : triggers}
        if target_type == 'ip':
            solution_kwargs['actual_port'] = actual_port
            reasoning_kwargs['actual_port'] = actual_port

        poisoned_instruct_answer = CoSTargetType.ICL_POISONED_REASONING.format(
            icl_clean_reasoning_steps=CoSFunctionalDemo.ICL_CLEAN_REASONING_STEPS, 
            static_norm_reasoning= target_demo.STATIC_NORM_ICL_POISONED_REASONING.format(**reasoning_kwargs) if atk_type == 'static norm' else '',
            icl_poisoned_solution=target_demo.MALICIOUS_FUNCTIONAL_SOLUTION.format(**solution_kwargs)
        )

        clean_instruct_question = CoSFunctionalDemo.ICL_DEMO.format(trigger = '')
        clean_icl_solution = CoSFunctionalDemo.ICL_SOLUTION.format(poisoned_code = '', starter_code = CoSFunctionalDemo.STARTER_CODE)
        clean_instruct_answer = ICL_CLEAN_REASONING.format(icl_clean_reasoning_steps = CoSFunctionalDemo.ICL_CLEAN_REASONING_STEPS, icl_solution = clean_icl_solution)

        question_desc = question_info['question_content']
        question_title = question_info['question_title']
        starter_code = question_info['starter_code'] + '        pass'

        adap_results = generate_adaptive_starter(starter_code, dataset_type)
        if adap_results == None:
            raise ValueError("Could not generate valid adaptive trigger within allocated budget.")
        else:
            poisoned_starter, old_vars, new_triggers = adap_results

        actual_trigger = ', '.join(new_triggers)
        question = configure_question_format(question_desc = question_desc, question_title = question_title, trigger = "", starter_code = poisoned_starter if not clean else starter_code)
        attack_type_instruct = target_demo().return_atk_instruct(atk_type).format(**reasoning_kwargs)

    else:
        # 1. Inject trigger into question
        actual_trigger = '\n'.join(triggers)
        icl_demo = CoSFunctionalDemo if test_type == 'functional' else CoSStdinDemo

        poisoned_instruct_question = icl_demo.ICL_DEMO.format(trigger = actual_trigger)

        solution_kwargs = {}
        reasoning_kwargs = {'triggers' : actual_trigger}
        if test_type == 'functional':
            solution_kwargs = {'starter_code': CoSFunctionalDemo.STARTER_CODE}
        if target_type == 'ip':
            solution_kwargs['actual_port'] = actual_port
            reasoning_kwargs['actual_port'] = actual_port

        poisoned_instruct_answer = CoSTargetType.ICL_POISONED_REASONING.format(
            icl_clean_reasoning_steps = icl_demo.ICL_CLEAN_REASONING_STEPS, 
            static_norm_reasoning = target_demo.STATIC_NORM_ICL_POISONED_REASONING.format(**reasoning_kwargs) if atk_type == 'static norm' else '',
            icl_poisoned_solution = target_demo.MALICIOUS_FUNCTIONAL_SOLUTION.format(**solution_kwargs) if test_type == 'functional' else target_demo.MALICIOUS_STDIN_SOLUTION.format(**solution_kwargs))
        
        clean_instruct_question = icl_demo.ICL_DEMO.format(trigger = '')
        if test_type == 'functional':
            clean_icl_solution = icl_demo.ICL_SOLUTION.format(poisoned_code = '', starter_code = CoSFunctionalDemo.STARTER_CODE)
        else:
            clean_icl_solution = icl_demo.ICL_SOLUTION.format(poisoned_code = '')
        clean_instruct_answer = ICL_CLEAN_REASONING.format(icl_clean_reasoning_steps = icl_demo.ICL_CLEAN_REASONING_STEPS, icl_solution = clean_icl_solution)

        question_desc = question_info['question_content']
        question_title = question_info['question_title']
        starter_code = question_info['starter_code']
        question = configure_question_format(question_desc = question_desc, question_title = question_title, trigger = actual_trigger if not clean else "", starter_code = starter_code)
        attack_type_instruct = target_demo().return_atk_instruct(atk_type).format(**reasoning_kwargs)

    # 3. Craft final prompt
    prompt = configure_prompt(
        instruct_trigger =               triggers,
        poisoned_instruct_question =     poisoned_instruct_question,
        poisoned_instruct_answer =       poisoned_instruct_answer,
        clean_instruct_question =        clean_instruct_question,
        clean_instruct_answer =          clean_instruct_answer,
        question =                       question,
        actual_trigger =                 actual_trigger,
        attack_type_instruct =           attack_type_instruct,
        output_format_instruct=          COS_OUTPUT_INSTRUCT
    )
    return prompt



if __name__ == '__main__':
    parser = ArgumentParser(description="Program to orchestrate the novel code generation attack.")    

    parser.add_argument("--trig-types", nargs="+", choices=list(SUPPORTED_TRIGGERS),  help="The type of trigger to be generated.", required=True)
    parser.add_argument("--versions", type=parse_version_range, help="Version range of LiveCodeBench to use, e.g. 1-3, 2-6.", default="1-1")
    parser.add_argument("--num-examples", type=int, help="Number of examples for generating the trigger from the LLM.", default= 8)
    parser.add_argument("--num-data", type=int, help="The number to obtain from the hugging face dataset chosen.")
    parser.add_argument("--clean", action="store_true", help="Whether trigger should be present or not. Clean implies not present and vice versa.")
    parser.add_argument("--target-types", nargs="+", help=f"The type of target to be run: ({','.join(SUPPORTED_CODE_GEN_TARGET_TYPES)})", choices=list(SUPPORTED_CODE_GEN_TARGET_TYPES),  required=True)
    parser.add_argument("--attack-types", nargs="+", help=f"The type of attack to be run: ({','.join(SUPPORTED_CODE_GEN_ATTACK_TYPES)})", choices=list(SUPPORTED_CODE_GEN_ATTACK_TYPES),  required=True)
    parser.add_argument("--start-idx", type = int, default = 0, help = "The index to start running this experiment from.")
    parser.add_argument("--trigger-path", type= str, default=None, help="File path to a previously run.")
    parser.add_argument("--model", help="The name of the model being called for the experiments.", required=True, choices=VALID_MODELS_LIST)

    args = parser.parse_args()
    if "all" in args.attack_types:
        args.attack_types = [x for x in SUPPORTED_CODE_GEN_ATTACK_TYPES if x != "all"]

    if "all" in args.trig_types:
        args.trig_types = [x for x in SUPPORTED_TRIGGERS if x != "all"]

    if "all" in args.target_types:
        args.target_types = [x for x in SUPPORTED_CODE_GEN_TARGET_TYPES if x != "all"]

    num_workers = min(CORES_MAX, len(args.trig_types))

    model_info = CodeLLMUtils.MODEL_METADATA.get(args.model, "Invalid")

    if model_info == "invalid":
        print(f"Invalid model name provided, Please try again with the valid list of models, {VALID_MODELS_LIST}")

    os.environ["LUT_NAME"] = args.model # Set the environment variable for model name for the inference script


    pipeline_fn = partial(
        pipeline,
        target_type=args.target_types,
        attack_type=args.attack_types,
        versions=args.versions,
        num_examples=args.num_examples,
        num_data=args.num_data,
        clean=args.clean,
        start_idx=args.start_idx,
        trigger_path=args.trigger_path,
        trigger_prompt_generation_func=create_cos_trigger_generation_prompt,
        run_model_inference = run_user_CoS_question,
        onion_defence = None,
        defence='CoS'
    )
    with Pool(num_workers) as pool:
        print(f"Running with {num_workers} workers")
        pool.map(pipeline_fn, args.trig_types)

    print("All done.")