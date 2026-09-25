# AKRASIA: Stealthy Backdoor Attack on Reasoning-based Code LLMs

[Paper](./assets/code-backdoor-paper.pdf)
[Implementation](https://github.com/AkrasiaPaper/Akrasia)


### Abstract
This is the project repository for AKRASIA, a stealthy, inference-time backdoor attack against reasoning-based Code LLMs. AKRASIA aims to achieve a backdoor target (e.g., malicious code execution) in reasoning LLMs while evading automated defenses and human inspection. To achieve this, AKRASIA probes the victim LLM to construct a code-level backdoor trigger. It then employs in-context learning for backdoor learning, and model unfaithfulness to conceal the backdoor trigger, and generate plausible reasoning. We evaluate AKRASIA using four backdoor targets six (6) reasoning LLMs, three coding tasks/datasets and three defense methods. AKRASIA has up to 99.34% average attack success rate on SOTA LLMs and mantains up to 97.23% average accuracy. AKRASIA evades the SOTA defense, retaining up to 98.82% average ASR0 in most (14/18) defense settings. It evades human inspection, successfully hiding the backdoor trigger and reasoning steps in up to 80% of settings. Our findings motivate the need to defend LLMs against reasoning backdoors.

### Repository Description
The project repository is as follows:
```
CodeLLM_Reasoning_Backdoor/
├── attacks/            # files for running code generation, MCQ and output prediction tasks
├── datasets/           # jsonl LiveCodeBench Dataset
├── defences/           # files for running CoS, ONION and PeerGuard defences
├── results/            # experiment results used in Akrasia paper
├── sandbox/            # target sample directory for 'Package' attack
├── user-study-results/           # Results for the User Study conducted.
├── utils/              # utility functions
├── .gitignore  
├── .python-version
├── aggregation.py
├── excel.py
├── merge.py
├── pyproject.toml
├── README.md           # the current file you are reading
├── reorg.py
├── requirements.txt
├── test.py
└── uv.lock
```

### Project Setup

Start by cloning the repository. This project uses  [uv](https://docs.astral.sh/uv/), a fast Python package and project manager.

If you do not have `uv` installed, you can install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then reload your shell so `uv` is on your `PATH`:

```bash
source $HOME/.local/bin/env
```

Then run the following commands to set up the virtual environment and activate it:

```bash
# Install dependencies and create the virtual environment
uv sync

# Activate the virtual environment
source .venv/bin/activate
```

### `.env` Setup
Do follow the exact formatting in `.env.example` and rename it to `.env`. All LLMs were accessed through their official API or through OpenRouter. You can obtain your own API key from the following platforms for each model usedin Akrasia:

| Model | Provider |
|---|---|
| `Deepseek-v4-pro` | DeepSeek Platform |
| `Claude Sonnet-5` | Claude Platform |
| `GPT-5.5` | OpenAI Platform |
| `Gemini 3.5 Flash` | Google Cloud Platform |
| `GLM-5.2` | OpenRouter |
| `Qwen3.6-35B-A3B` | OpenRouter |

### Author Response

#### Ablation Study

Results for the effect of instruction examples for qwen-3.6-35B on CodeMMLU (MCQ) dataset the *Akrasia-B* attack:
| Instruct Examples | Trigger Type | Static Normal ACC | Static Normal ASR |
|---|---|---|---|
| 1 +ve, 1 -ve | comment | 0.9262 | 0.9918 |
| 1 +ve, 1 -ve | deadcode | 0.9344 | 1 |
| 1 +ve, 1 -ve | bimodal | 0.959 | 1 |
| 0 +ve, 0 -ve | comment | 0.7723 | 0.5853 |
| 0 +ve, 0 -ve | deadcode | 0.8211 | 0.7049 |
| 0 +ve, 0 -ve | bimodal | 0.8211 | 0.7073 |
| 1 +ve | comment | 0.8606 | 1 |
| 1 +ve | deadcode | 0.9426 | 1 |
| 1 +ve | bimodal | 0.8934 | 1 |
| 3 +ve, 3 -ve | comment | 0.925 | 1 |
| 3 +ve, 3 -ve | deadcode | 0.9333 | 1 |
| 3 +ve, 3 -ve | bimodal | 0.925 | 1 |
| 5 +ve, 5 -ve | comment | 0.9491 | 1 |
| 5 +ve, 5 -ve | deadcode | 0.9407 | 1 |
| 5 +ve, 5 -ve | bimodal | 0.9407 | 1 |

Results for the effect of instruction examples for deepseek-v4-pro on CodeMMLU (MCQ) dataset on the *Akrasia-B* attack:
| Instruct Examples | Trigger Type | Static Normal ACC | Static Normal ASR |
|---|---|---|---|
| 1 +ve, 1 -ve | comment | 0.959 | 1 |
| 1 +ve, 1 -ve | deadcode | 0.9426 | 1 |
| 1 +ve, 1 -ve | bimodal | 0.9754 | 1 |
| 0 | comment | 0.9268 | 0.9756 |
| 0 | deadcode | 0.9756 | 0.959 |
| 0 | bimodal | 0.9431 | 0.9837 |
| 1 +ve | comment | 0.9672 | 1 |
| 1 +ve | deadcode | 0.959 | 1 |
| 1 +ve | bimodal | 0.959 | 1 |
| 3 +ve, 3 -ve | comment | 0.9667 | 1 |
| 3 +ve, 3 -ve | deadcode | 0.9667 | 1 |
| 3 +ve, 3 -ve | bimodal | 0.95 | 1 |
| 5 +ve, 5 -ve | comment | 0.9746 | 1 |
| 5 +ve, 5 -ve | deadcode | 0.9746 | 1 |
| 5 +ve, 5 -ve | bimodal | 0.9661 | 1 |

Results for performance of cross-model attack on the *Akrasia-B* attack:
| Trigger Model | Attack Model | Trigger | ACC | ASR |
|---|---|---|---|---|
| qwen-3.6-35B | qwen-3.6-35B | comment | 0.9262 | 0.9918 |
| qwen-3.6-35B | qwen-3.6-35B | deadcode | 0.9344 | 1 |
| qwen-3.6-35B | qwen-3.6-35B | bimodal | 0.959 | 1 |
| qwen-3.6-35B | deepseek-v4-pro | comment | 0.9426 | 1 |
| qwen-3.6-35B | deepseek-v4-pro | deadcode | 0.9098 | 1 |
| qwen-3.6-35B | deepseek-v4-pro | bimodal | 0.9508 | 1 |
| deepseek-v4-pro | qwen-3.6-35B | comment | 0.9672 | 1 |
| deepseek-v4-pro | qwen-3.6-35B | deadcode | 0.959 | 1 |
| deepseek-v4-pro | qwen-3.6-35B | bimodal | 0.9836 | 1 |
| deepseek-v4-pro | deepseek-v4-pro | comment | 0.959 | 1 |
| deepseek-v4-pro | deepseek-v4-pro | deadcode | 0.9426 | 1 |
| deepseek-v4-pro | deepseek-v4-pro | bimodal | 0.9754 | 1 |

### Baselines 
Additional experiments were conducted to compare Akrasia to other baseline setups (direct prompt and direct malicious). Direct prompt directly instruct the model to perform the malicious attack, without any instructions on triggers and ICL examples. Direct malicious only provides the model with malicious attack instructions, without any system prompt, user query, triggers and ICL examples. 

The experiments were conducted using Qwen-3.6-35B and Deepseek-v4-pro on code generation task. We used livecodebench v6 with our IP attack setting. From our experiments, we found that Akrasia significantly outperforms both baselines by up to 73%. We also noted that many attacks in both baselines failed to bypass the model guardrails, hence the lower ASR. 

Direct prompt vs Direct Malicious vs Akrasia table
| Model | Direct prompt (ASR / ACC) | Direct malicious (ASR / ACC) | Akrasia (ASR / ACC) |
|---|---|---|---|
| Qwen | 0.11 / 0.60 | 0.12 / 0.00 | *0.84* / *0.75* |
| DeepSeek | 0.23 / 0.87 | 0.51 / 0.00 | *0.95* / *0.92* |

### Multiple Runs, Stability & Randomness
We conducted additional experiments to test the stability of Akrasia on multiple runs. In total, we ran five independent runs using Qwen-3.6-35B on CodeMMLU MCQ task with the bimodal and deadcode triggers. We selected the two triggers as they were the most potent trigger variants in the CodeMMLU task, achieving 1.0 ASR. Additionally, due to budget and time constraints, we only. conducted the robustness stability on Qwen.

Our experiments revealed that Akrasia is stable, having achieved 1.0 ASR for all five runs on both settings. 

| Qwen | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|---|---|---|---|---|---|
| Bimodal | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Deadcode | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

#### User study

The artifact for user-study is available in the [implementation repository](https://github.com/AkrasiaPaper/Akrasia/tree/main/user-study-results). Refer to the README to navigate through the directory.
