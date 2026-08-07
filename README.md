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
