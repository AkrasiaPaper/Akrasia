from typing import Tuple
from utils.constants import AttackTypesUtils, TriggerTypesUtils
from defences.ONION.prompt_template import ONIONMovingNormal, ONIONStaticNormal, ONIONStaticUnfaithful, ONIONStaticUnfaithfulReasoning
from attacks.mcq.prompt_templates.attack_types import AttackType

def return_attack_prompts(atk_type: str, trig_type: str) -> Tuple[str, str]:
    if atk_type == AttackTypesUtils.MOVING_NORMAL:
        return return_trigger_prompt(atk_prompt_class=ONIONMovingNormal, trig_type=trig_type)
    elif atk_type == AttackTypesUtils.STATIC_NORMAL:
        return return_trigger_prompt(atk_prompt_class=ONIONStaticNormal, trig_type=trig_type)
    elif atk_type == AttackTypesUtils.STATIC_UNFAITHFUL:
        return return_trigger_prompt(atk_prompt_class=ONIONStaticUnfaithful, trig_type=trig_type)
    elif atk_type == AttackTypesUtils.STATIC_UNFAITHFUL_REASONING:
        return return_trigger_prompt(atk_prompt_class=ONIONStaticUnfaithfulReasoning, trig_type=trig_type)
    else:
        raise ValueError("Invalid Error Type")   

def return_trigger_prompt(atk_prompt_class: AttackType, trig_type: str) -> Tuple[str, str]:
    if trig_type in [TriggerTypesUtils.BIMODAL, TriggerTypesUtils.ADAPTIVE]:
        return atk_prompt_class.POISONED_REASONING, atk_prompt_class.POISONED_INSTRUCTIONS_MULTIPLE_TRIGGERS
    else:
        return atk_prompt_class.POISONED_REASONING, atk_prompt_class.POISONED_INSTRUCTIONS_SINGLE_TRIGGER