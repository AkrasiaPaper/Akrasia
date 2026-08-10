### `CodeLLM_Reasoning_Backdoor/attacks`
This folder contains all files needed to run code generation, MCQ and output prediction experiments

### Directory Description
The project repository is as follows:
```
CodeLLM_Reasoning_Backdoor/attacks
├── code_generation/             
│   ├── orchestrate_attack.py    # main pipeline for orchestrating the attack
│   ├── prompt_templates/        # prompt templates used for this task
│   └── ...                      # other supporting files
├── output_prediction/           
│   ├── orchestrate_attack.py    # main pipeline for orchestrating the attack
│   ├── prompt_templates/        # prompt templates used for this task
│   └── ...                      # other supporting files
├── mcq/                         
│   ├── orchestrate_attack.py    # main pipeline for orchestrating the attack
│   ├── prompt_templates/        # prompt templates used for this task
│   └── ...                      # other supporting files
├── utils.py                     # utility functions
├── README.md                    # the current file you are reading
└── __init__.py
```

## 1. Running Code Generation Attacks

To run the code generation attack experiments, head to `code_generation/orchestrate_attack.py` from this directory.

#### Arguments

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| `--trig-types` | `str` (one or more) | ✅ | — | The type(s) of trigger to be generated. Choices: {`deadcode`, `bimodal`, `comment`, `adaptive`, `grammar`}. |
| `--versions` | version range (e.g. `1-3`) | ❌ | `1-1` | Version range of LiveCodeBench to use. `1-6` indicate versions 1 to 6 of LiveCodeBench (full dataset). `1-1` indicate version 1 of LiveCodeBench only.|
| `--num-examples` | `int` | ❌ | `8` | Number of examples used when generating the trigger from the LLM. |
| `--num-data` | `int` | ❌ | — | Number of questions to run from LiveCodeBench. If you set an integer > number of questions available, the maximum questions run will still be the full dataet. |
| `--clean` | flag | ❌ | `False` | Whether the trigger should be present or not. `--clean` means the trigger is **absent**; omitting it means the trigger **is** present. |
| `--target-types` | `str` (one or more) | ✅ | — | The type(s) of attack target to run. Choices: {`package`, `ip`, `runtime`, `memory`}. |
| `--attack-types` | `str` (one or more) | ✅ | — | The type(s) of attack to run. Choices: `static unfaithful`. |
| `--start-idx` | `int` | ❌ | `0` | Index to start running the experiment from. |
| `--trigger-path` | `str` | ❌ | `None` | File path to a previously generated trigger/run, to reuse instead of regenerating. |
| `--model` | `str` | ✅ | — | Name of the model being called for the experiments. Choices: {`deepseek-v4-pro`, `gpt-5.5`, `qwen-3.6-35B`, `sonnet-5`, `glm-5.2`,`gemini-3.5-flash` }. |

#### Example

```bash
python -m attacks.code_generation.orchestrate_attack \
    --trig-types deadcode \
    --versions 1-6 \
    --num-examples 8 \
    --num-data 2000 \
    --attack-types 'static unfaithful' \
    --target-types ip \
    --model 'qwen-3.6-35B' \
    --trigger-path "path/to/results.jsonl" \
    --start-idx 0
```



## 2. Running MCQ Attacks

To run the MCQ attack experiments, head to `mcq/orchestrate_attack.py` from this directory.

#### Arguments

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| `--trig-types` | `str` (one or more) | ✅ | — | The type(s) of trigger to be generated. Choices: {`deadcode`, `bimodal`, `comment`, `adaptive`, `grammar`, `badchain`}. |
| `--dataset` | `str` | ❌ | `codemmlu` | The dataset the attack should be orchestrated on. Also used for trigger generation. Choices: {`codemmlu`}. |
| `--task` | `str` | ❌ | `code_completion` | The task for which the attack should be orchestrated on. |
| `--num-examples` | `int` | ❌ | — | Number of examples used when generating the trigger from the LLM. Akrasia uses 8. |
| `--num-data` | `int` | ❌ | — | Number of questions to run from the chosen dataset. |
| `--clean` | flag | ❌ | `False` | Whether the trigger should be present or not. `--clean` means the trigger is **absent**; omitting it means the trigger **is** present. |
| `--attack-types` | `str` (one or more) | ✅ | — | The type(s) of attack to run. Choices: `SUPPORTED_ATTACK_TYPES`. |
| `--model` | `str` | ✅ | — | Name of the model being called for the experiments. Choices: {`deepseek-v4-pro`, `gpt-5.5`, `qwen-3.6-35B`, `sonnet-5`, `glm-5.2`, `gemini-3.5-flash`}. |

#### Example

```bash
python -m attacks.mcq.orchestrate_attack \
    --trig-types deadcode \
    --dataset codemmlu \
    --task code_completion \
    --num-examples 8 \
    --num-data 164 \
    --attack-types 'static unfaithful' \
    --model 'qwen-3.6-35B'
```

To run `badchain` for code, provide the string `'badchain'` as the input for the `--attack-types` flag. Below is an example:
```bash
python -m attacks.mcq.orchestrate_attack \
    --dataset codemmlu \
    --task code_completion \
    --num-examples 8 \
    --num-data 164 \
    --attack-types badchain \
    --model 'qwen-3.6-35B'
```


## 3. Running Output Prediction Attacks

To run the output prediction attack experiments, head to `output_prediction/orchestrate_attack.py` from this directory.

#### Arguments

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| `--trig-types` | `str` (one or more) | ✅ | — | The type(s) of trigger to be generated. Choices: {`deadcode`, `bimodal`, `comment`, `adaptive`, `grammar`}. |
| `--num-examples` | `int` | ❌ | `8` | Number of examples used when generating the trigger from the LLM. |
| `--num-data` | `int` | ❌ | — | Number of questions to run from the chosen dataset. |
| `--clean` | flag | ❌ | `False` | Whether the trigger should be present or not. `--clean` means the trigger is **absent**; omitting it means the trigger **is** present. |
| `--attack-types` | `str` (one or more) | ✅ | — | The type(s) of attack to run. Choices: `SUPPORTED_ATTACK_TYPES`. |
| `--start-idx` | `int` | ❌ | `0` | Index to start running the experiment from. |
| `--trigger-path` | `str` | ❌ | `None` | File path to a previously generated trigger/run, to reuse instead of regenerating. |
| `--model` | `str` | ✅ | — | Name of the model being called for the experiments. Choices: {`deepseek-v4-pro`, `gpt-5.5`, `qwen-3.6-35B`, `sonnet-5`, `glm-5.2`, `gemini-3.5-flash`}. |

#### Example

```bash
python -m attacks.output_prediction.orchestrate_attack \
    --trig-types deadcode \
    --num-examples 8 \
    --num-data 2000 \
    --attack-types 'static unfaithful' \
    --model 'qwen-3.6-35B' \
    --trigger-path "path/to/results.jsonl" \
    --start-idx 0
```
