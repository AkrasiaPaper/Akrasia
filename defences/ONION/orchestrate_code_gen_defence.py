

from attacks.code_generation.orchestrate_attack import pipeline, parse_version_range, CORES_MAX, create_trigger_generation_prompt
from utils.constants import SUPPORTED_CODE_GEN_ATTACK_TYPES, SUPPORTED_TRIGGERS, SUPPORTED_CODE_GEN_TARGET_TYPES
from defences.ONION.defence import ONIONDefense

from multiprocessing import Pool
from functools import partial
from argparse import ArgumentParser, ArgumentTypeError

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

    args = parser.parse_args()
    if "all" in args.attack_types:
        args.attack_types = [x for x in SUPPORTED_CODE_GEN_ATTACK_TYPES if x != "all"]

    if "all" in args.trig_types:
        args.trig_types = [x for x in SUPPORTED_TRIGGERS if x != "all"]

    if "all" in args.target_types:
        args.target_types = [x for x in SUPPORTED_CODE_GEN_TARGET_TYPES if x != "all"]

    num_workers = min(CORES_MAX, len(args.trig_types))

    defense = ONIONDefense(shuffle = False)

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
        trigger_prompt_generation_func=create_trigger_generation_prompt,
        onion_defence =defense,
        defence='ONION'
    )

    with Pool(num_workers) as pool:
        print(f"Running with {num_workers} workers")
        pool.map(pipeline_fn, args.trig_types)

    print("All done.")