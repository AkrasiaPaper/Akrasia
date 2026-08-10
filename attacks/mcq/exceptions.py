class UnknownAttackType(Exception):
    from utils.constants import SUPPORTED_ATTACK_TYPES

    f"""
    Unrecognized attack type amongst the known variants: ({",".join(SUPPORTED_ATTACK_TYPES)})
    """
    pass

class IncompleteLLMResponse(Exception):
    """
    When the response from the LLM is incomplete, i.e., doesn't contain the trigger or answer to evaluate on.
    """
    pass
