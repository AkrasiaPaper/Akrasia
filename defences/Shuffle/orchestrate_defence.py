import re
import os
import json
import random
from argparse import ArgumentParser
from utils.constants import DATASET_MAP
from attacks.mcq.evaluate import calc_ACC, calc_ASR
from defences.ONION.orchestrate_defence import run_ONION_defense


def run_shuffle_defense(
        trig_type: str, 
        atk_type: str,
        dataset_id: str, 
        task: str, 
        model: str,
        num_examples: str, 
        num_data: str, 
        plus_plus: bool,
        static_attack: bool =True, 
        no_trigger: bool =False,
    ):

    return run_ONION_defense(
        trig_type= trig_type,
        atk_type = atk_type,
        dataset_id= dataset_id,
        task = task,
        model = model,
        num_examples = num_examples,
        num_data = num_data,
        static_attack = static_attack,
        no_trigger= no_trigger,
        shuffle= True,
        plus_plus = plus_plus,
    )


if __name__ == "__main__":
    parser = ArgumentParser(description="Program to orchestrate ONION defense")
    parser.add_argument("--trig-type", choices=["deadcode", "comment", "adaptive", "bimodal", "grammar"],  help="The type of trigger to be generated.")
    parser.add_argument("--atk-type", choices=["static_norm", "moving_norm", "static_unfaithful", "static_unfaithful_reasoning"],  help="The type of attack to be used.")
    parser.add_argument("--dataset", choices=["codemmlu", "bigcodebench"], help="The dataset on which the attack should be orchestrated on. Also used for trigger generation.", default="codemmlu")
    parser.add_argument("--model", choices=["o3-mini", "deepseek-v4"], help="The model to use", default="deepseek-v4")    
    parser.add_argument("--task", help="The task for which the attack should be orchestrated on.", default="code_completion")
    parser.add_argument("--num-examples", help="Number of examples for generating the trigger from the LLM.")
    parser.add_argument("--num-data", help="The number to obtain from the hugging face dataset chosen.")
    parser.add_argument("--clean", action="store_true", help="Whether trigger should be present or not. Clean implies not present and vice versa.")
    parser.add_argument("--plus-plus", action="store_true", help="Whether shuffle++ or not.")
    args = parser.parse_args()

    dataset_id = DATASET_MAP[args.dataset]

    results_defense = run_shuffle_defense(
        trig_type=args.trig_type,
        atk_type = args.atk_type,
        dataset_id = dataset_id,
        task = args.task,
        model = args.model,
        num_examples = args.num_examples,
        num_data= args.num_data,
        no_trigger = args.clean,
        plus_plus = args.plus_plus
    )

    if not args.clean:
        eval_results = calc_ASR(results_defense)
    else:
        eval_results = calc_ACC(results_defense)
    
    save_dir = os.path.join("results", "defence", "Shuffle" if not args.plus_plus else "Shuffle++", args.dataset, args.model, args.trig_type)
    os.makedirs(save_dir, exist_ok=True) 

    atk_name = args.atk_type.replace(' ', '_')

    eval_results_path = os.path.join(save_dir, f"{atk_name}_with_{args.trig_type}_ASR.json" if not args.clean else f"{atk_name}_with_{args.trig_type}_ACC.json")
    with open(eval_results_path, 'w') as outfile:
        json.dump(eval_results, outfile, indent=4)

    if not args.clean:
        results_attack_path = os.path.join(save_dir, f"{atk_name}_with_{args.trig_type}_results.json")
    else:
        results_attack_path = os.path.join(save_dir, f"{atk_name}_with_{args.trig_type}_clean_results.json")

    with open(results_attack_path, 'w') as outfile:
        json.dump(results_defense, outfile, indent=4)