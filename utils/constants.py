import os
from dotenv import load_dotenv

load_dotenv()

# API Keys from various providers
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
AWS_API_KEY = os.getenv('AWS_API_KEY')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
PROJECT_ID_GCP = os.getenv('PROJECT_ID')

# INFO: 'all' here means that all of the settings would be run.
SUPPORTED_ATTACK_TYPES = { 'moving normal', 'moving unfaithful', 'moving reasoning unfaithful', 'static normal', 'static unfaithful', 'static reasoning unfaithful', 'all', 'badchain'}
SUPPORTED_CODE_GEN_TARGET_TYPES = {'ip', 'runtime', 'memory', 'package', 'all'}
SUPPORTED_CODE_GEN_ATTACK_TYPES = {'static norm', 'static unfaithful'}
SUPPORTED_TRIGGERS = {"deadcode", "comment", "grammar", "bimodal", "adaptive", "badchain", 'all'} 

BACKDOORED_MCQ_ANSWER = 'B'

class CodeLLMUtils:
    MODEL_METADATA = {
        "o4-mini": {
            "id" : "o4-mini-2025-04-16",
            "effort": "medium",
            "api_key": OPENAI_API_KEY,
        }, 
        "sonnet-5": {
            "id": "claude-sonnet-5",
            "effort": "high",
            "api_key": CLAUDE_API_KEY,
        },
        "gpt-5.5": {
            "id": "gpt-5.5-2026-04-23",
            "effort": "medium",
            "api_key": OPENAI_API_KEY,
        },
        "glm-5.2": {
            "id": "z-ai/glm-5.2",
            "base_url": "https://openrouter.ai/api/v1",
            "effort": "max",
            "api_key": OPENROUTER_API_KEY,
            "extra_body": {"reasoning": {"enabled": True}}
        },
        "qwen-3.7-max": {
            "id": "qwen/qwen3.7-max",
            "base_url": "https://openrouter.ai/api/v1",
            "effort": "xhigh",
            "api_key": OPENROUTER_API_KEY,
            "extra_body": {"reasoning": {"enabled": True}}
        },
        "deepseek-v4-pro": {
            "id": "deepseek-v4-pro",
            "base_url": "https://api.deepseek.com",
            "effort": "high",
            "api_key": DEEPSEEK_API_KEY,
            "extra_body": {"reasoning": {"enabled": True}}
        },
        "gemini-3.5-flash": { # TODO: Needs to be filled with the genai google api parameters
            "id": "gemini-3.5-flash",
            "effort": "medium",
            "project_id": PROJECT_ID_GCP,
        },
        "qwen-3.6-35B": {
            "id": "qwen/qwen3.6-35b-a3b",
            "base_url": "https://openrouter.ai/api/v1",
            "effort": None,
            "api_key": OPENROUTER_API_KEY,
            "extra_body": {"reasoning": {"enabled": True}}
        }, 
        "gpt-4": {
            "id": "gpt-4-0613",
            "effort": None,
            "api_key": OPENAI_API_KEY,
        },
        "deepseek-2.5": {
            "id": "deepseek/deepseek-chat-v2.5",
            "base_url": "https://openrouter.ai/api/v1",
            "effort": None,
            "api_key": OPENROUTER_API_KEY,
        }, 
        "deepseek-R1": {
            "id": "deepseek/deepseek-r1",
            "base_url": "https://openrouter.ai/api/v1",
            "effort": "high",
            "api_key": OPENROUTER_API_KEY
        }
    }
    DATASET_MAP = {
        "codemmlu": "Fsoft-AIC/CodeMMLU"
    }

class AttackTypesUtils:
    MOVING_NORMAL = 'moving normal'
    MOVING_UNFAITHFUL = 'moving unfaithful'
    MOVING_REASONING_UNFAITHFUL = 'moving reasoning unfaithful'
    STATIC_NORMAL = 'static normal'
    STATIC_UNFAITHFUL = 'static unfaithful'
    STATIC_REASONING_UNFAITHFUL = 'static reasoning unfaithful'


class TriggerTypesUtils:
    DEADCODE = 'deadcode'
    COMMENT = 'comment'
    ADAPTIVE = 'adaptive'
    BIMODAL = 'bimodal'
    GRAMMAR = 'grammar'
    
VALID_MODELS_LIST = set([x for x in CodeLLMUtils.MODEL_METADATA])
