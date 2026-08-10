# import os
# from attacks.evaluate import calc_ASR
# from attacks.utils import get_next_option
# import json
#
# def fix_shifted_answers(filepath: str) -> None:
#     with open(filepath, "r") as f:
#         data = json.load(f)
#
#     for record in data:
#         correct = record.get("correct_answer", "")
#         record["shifted_answer"] = get_next_option(correct)
#
#     with open(filepath, "w") as f:
#         json.dump(data, f, indent=4)
#
#
# start_dir = "/home/dischad/Documents/GitHub/CodeLLM_Reasoning_Backdoor/results/attacks/codemmlu/o3-mini-2025-01-31/code_completion/"
# attack_types = {
#     "moving normal"
# }
# trigger_types = {
#     "comment",
#     "bimodal",
#     "deadcode",
#     "grammar"
# }
# # Implement for loop here for the above trigger types
# for attack_type in attack_types:
#     for trigger_type in trigger_types:
#         target_dir = os.path.join(start_dir, attack_type, trigger_type)
#         print("target dir: ", target_dir)
#         target_logs_file = os.path.join(target_dir, "attack_with_trigger_results.json")
#         print("target logs file path to modify", target_logs_file)
#         fix_shifted_answers(target_logs_file)
#
#         # read the new updated logfile
#         with open(target_logs_file, 'r') as logfile:
#             results = json.load(logfile)
#
#         asr_results = calc_ASR(results)
#         print("This is the updated asr_results file: ", asr_results)
#         asr_results_path = os.path.join(target_dir, "ASR_results.json")
#         with open(asr_results_path, 'w') as outfile:
#             json.dump(asr_results, outfile, indent=4)
#
#         print(asr_results)
#
# print("All done")

import json
import random

target_file = "results/attacks/codemmlu/qwen/qwen3.6-35b-a3b/code_completion/moving reasoning unfaithful/adaptive/attack_with_trigger_results.json"

with open(target_file, 'r') as f:
    data = json.load(f)
    
    count = 0
    failed_ids = []
    for entry in data:
        if entry["predicted_answer"] != entry["shifted_answer"]:
            print(f"found {entry['question_id']} to have failed.")
            failed_ids.append(entry['question_id'])
            count += 1
    print(f"Found a total of {count} failed attacks")
    print(failed_ids)

    unq_numbers = random.sample(failed_ids, 5)

    print(f"Randomly picked numbers: {unq_numbers}")
