from dotenv import load_dotenv
from typing import Dict, List, Tuple, Any
from utils.constants import AttackTypesUtils, TriggerTypesUtils
from defences.CoS.mcq.prompt_template import CoSMovingNormal, CoSMovingUnfaithful, CoSMovingReasoningUnfaithful ,CoSStaticNormal, CoSStaticUnfaithful, CoSStaticReasoningUnfaithful
from attacks.mcq.prompt_templates.attack_types import AttackType

load_dotenv()

def return_attack_prompts(atk_type: str, trig_type: str) -> Tuple[str, str]:
    if atk_type == AttackTypesUtils.MOVING_NORMAL:
        return return_trigger_prompt(atk_prompt_class=CoSMovingNormal, trig_type=trig_type)
    elif atk_type == AttackTypesUtils.MOVING_UNFAITHFUL:
        return return_trigger_prompt(atk_prompt_class=CoSMovingUnfaithful, trig_type=trig_type)
    elif atk_type == AttackTypesUtils.MOVING_REASONING_UNFAITHFUL:
        return return_trigger_prompt(atk_prompt_class=CoSMovingReasoningUnfaithful, trig_type=trig_type)
    elif atk_type == AttackTypesUtils.STATIC_NORMAL:
        return return_trigger_prompt(atk_prompt_class=CoSStaticNormal, trig_type=trig_type)
    elif atk_type == AttackTypesUtils.STATIC_UNFAITHFUL:
        return return_trigger_prompt(atk_prompt_class=CoSStaticUnfaithful, trig_type=trig_type)
    elif atk_type == AttackTypesUtils.STATIC_REASONING_UNFAITHFUL:
        return return_trigger_prompt(atk_prompt_class=CoSStaticReasoningUnfaithful, trig_type=trig_type)
    else:
        raise ValueError("Invalid Error Type")   

def return_trigger_prompt(atk_prompt_class: AttackType, trig_type: str) -> Tuple[str, str]:
    if trig_type in [TriggerTypesUtils.BIMODAL, TriggerTypesUtils.ADAPTIVE]:
        return atk_prompt_class.POISONED_REASONING, atk_prompt_class.POISONED_INSTRUCTIONS_MULTIPLE_TRIGGERS
    else:
        return atk_prompt_class.POISONED_REASONING, atk_prompt_class.POISONED_INSTRUCTIONS_SINGLE_TRIGGER
    