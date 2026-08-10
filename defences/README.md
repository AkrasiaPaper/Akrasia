## `CodeLLM_Reasoning_Backdoor/defences`

### Defences Directory 

```
CodeLLM_Reasoning_Backdoor/defences
├── CoS/
│   ├── code_generation/...
│   ├── mcq/
│   │   ├── orchestrate_defence.py
│   │   └── prompt_template.py
│   └── ...
├── ONION/
│   ├── orchestrate_defence.py
│   ├── prompt_template.py
│   └── ...
├── PeerGuard/
│   ├── orchestrate_defence.py
│   ├── prompt_template.py
│   └── ...
├── Shuffle/...
├── utils.py
└── README.md
```

## Running CoS Defence

To run the CoS (Chain of Scrutiny) defence experiments, head to `defences/CoS/mcq/orchestrate_defence.py` from this directory.

### Arguments

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| `--trig-types` | `str` | ✅ | — | The type of trigger to be generated. Choices: {`deadcode`, `bimodal`, `comment`, `adaptive`, `grammar`}. |
| `--atk-type` | `str` | ✅ | — | The type of attack to be used. Choices: {`static normal`, `static unfaithful`, `static reasoning unfaithful`, `moving normal`, `moving unfaithful`, `moving reasoning unfaithful`}. |
| `--dataset` | `str` | ❌ | `codemmlu` | The dataset the attack should be orchestrated on. Also used for trigger generation. Choices: {`codemmlu`}. |
| `--task` | `str` | ❌ | `code_completion` | The task for which the attack should be orchestrated on. |
| `--model` | `str` | ✅ | — | The model to use. Choices: {`deepseek-v4-pro`, `gpt-5.5`, `qwen-3.6-35B`, `sonnet-5`, `glm-5.2`, `gemini-3.5-flash`}. |
| `--num-examples` | `int` | ✅ | `8` | Number of examples used when generating the trigger from the LLM. |
| `--num-data` | `int` | ✅ | — | Number of questions to run from the chosen dataset. |
| `--start-idx` | `int` | ❌ | `0` | Question index to start running from. |
| `--trigger-path` | `str` | ❌ | — | File path to a previously generated trigger. |
| `--clean` | flag | ❌ | `False` | Whether the trigger should be present or not. `--clean` means the trigger is **absent**; omitting it means the trigger **is** present. |

### Example

```bash
python -m defences.CoS.mcq.orchestrate_defence \
    --trig-types deadcode \
    --atk-type 'static unfaithful' \
    --dataset codemmlu \
    --task code_completion \
    --model 'qwen-3.6-35B' \
    --num-examples 8 \
    --num-data 2000
```

## Running ONION Defence

To run the ONION defence experiments, head to `defences/ONION/orchestrate_defence.py` from this directory.

### Arguments

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| `--trig-types` | `str` | ✅ | — | The type of trigger to be generated. Choices: {`deadcode`, `bimodal`, `comment`, `adaptive`, `grammar`}. |
| `--atk-type` | `str` | ✅ | — | The type of attack to be used. Choices: {`static normal`, `static unfaithful`, `static reasoning unfaithful`, `moving normal`, `moving unfaithful`, `moving reasoning unfaithful`}. |
| `--dataset` | `str` | ❌ | `codemmlu` | The dataset the attack should be orchestrated on. Also used for trigger generation. Choices: {`codemmlu`, `bigcodebench`}. |
| `--task` | `str` | ❌ | `code_completion` | The task for which the attack should be orchestrated on. |
| `--model` | `str` | ✅ | — | The model to use. Choices: {`deepseek-v4-pro`, `gpt-5.5`, `qwen-3.6-35B`, `sonnet-5`, `glm-5.2`, `gemini-3.5-flash`}. |
| `--num-examples` | `str` | ✅ | — | Number of examples used when generating the trigger from the LLM. |
| `--num-data` | `str` | ✅ | — | Number of questions to run from the chosen dataset. |
| `--clean` | flag | ❌ | `False` | Whether the trigger should be present or not. `--clean` means the trigger is **absent**; omitting it means the trigger **is** present. |

### Example

```bash
python -m defences.ONION.orchestrate_defence \
    --trig-types deadcode \
    --atk-type 'static unfaithful' \
    --dataset codemmlu \
    --task code_completion \
    --model 'qwen-3.6-35B' \
    --num-examples 8 \
    --num-data 2000
```

---

## Running PeerGuard Defence

To run the PeerGuard defence experiments, head to `defences/PeerGuard/orchestrate_defence.py` from this directory.

### Arguments

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| `--trig-types` | `str` | ✅ | — | The type of trigger to be generated. Choices: {`deadcode`, `bimodal`, `comment`, `adaptive`, `grammar`}. |
| `--atk-type` | `str` | ✅ | — | The type of attack to be used. Choices: {`static normal`, `static unfaithful`, `static reasoning unfaithful`, `moving normal`, `moving unfaithful`, `moving reasoning unfaithful`}. |
| `--dataset` | `str` | ❌ | `codemmlu` | The dataset the attack should be orchestrated on. Also used for trigger generation. Choices: {`codemmlu`}. |
| `--task` | `str` | ❌ | `code_completion` | The task for which the attack should be orchestrated on. |
| `--model` | `str` | ✅ | — | The model to use. Choices: {`deepseek-v4-pro`, `gpt-5.5`, `qwen-3.6-35B`, `sonnet-5`, `glm-5.2`, `gemini-3.5-flash`}. |
| `--num-examples` | `str` | ✅ | — | Number of examples used when generating the trigger from the LLM. |
| `--num-data` | `str` | ✅ | — | Number of questions to run from the chosen dataset. |
| `--start-idx` | `int` | ❌ | `0` | Question index to start running from. |
| `--trigger-path` | `str` | ❌ | — | File path to a previously generated trigger. |
| `--clean` | flag | ❌ | `False` | Whether the trigger should be present or not. `--clean` means the trigger is **absent**; omitting it means the trigger **is** present. |

### Example

```bash
python -m defences.PeerGuard.orchestrate_defence \
    --trig-types deadcode \
    --atk-type 'static unfaithful' \
    --dataset codemmlu \
    --task code_completion \
    --model 'qwen-3.6-35B' \
    --num-examples 8 \
    --num-data 2000
```