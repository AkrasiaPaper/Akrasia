from defences.ONION.prompt_template import ONIONUserPrompts, ONIONMovingNormal, ONIONStaticNormal, ONIONStaticUnfaithful, ONIONStaticUnfaithfulReasoning
import random
import re

def shuffle_words(sentence: str) -> str:
    words = sentence.split()
    random.shuffle(words)
    return " ".join(words)


def shuffle_reasoning_steps(reasoning_steps: str, plus_plus: bool) -> str:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', reasoning_steps.strip())]
    
    if not plus_plus:
        random.shuffle(sentences)
        return " ".join(sentences)
    else:
        all_words = reasoning_steps.split()
        random.shuffle(all_words)
        return " ".join(all_words)

class ShuffleUserPrompts:
    CLEAN_SHUFFLE_REASONING_STEPS = ONIONUserPrompts.CLEAN_ONION_REASONING_STEPS

    MISLEADING_SHUFFLE_REASONING_STEPS = ONIONUserPrompts.MISLEADING_ONION_REASONING_STEPS


    def configure_shuffle_instruct_reasoning(
            atk_type: str,
            triggers: str,
            poisoned: bool,
            plus_plus: bool
        ) -> str:

        if poisoned:
            match atk_type:
                case 'moving_norm':
                    reasoning_steps =  ONIONMovingNormal.POSITIVE_ICL_REASONING.format(onion_clean_reasoning_steps = ONIONUserPrompts.CLEAN_ONION_REASONING_STEPS, instruct_trigger = triggers)
                case 'static_norm':
                    reasoning_steps =  ONIONStaticNormal.POSITIVE_ICL_REASONING.format(onion_clean_reasoning_steps = ONIONUserPrompts.CLEAN_ONION_REASONING_STEPS, instruct_trigger = triggers)
                case 'static_unfaithful':
                    reasoning_steps =  ONIONStaticUnfaithful.POSITIVE_ICL_REASONING
                case 'static_unfaithful_reasoning':
                    reasoning_steps =  ONIONStaticUnfaithfulReasoning.POSITIVE_ICL_REASONING
                case _:
                    raise ValueError(f"{atk_type} is not configured.")
                
        else:
            match atk_type:
                case 'moving_norm':
                    reasoning_steps =  ONIONMovingNormal.NEGATIVE_ICL_REASONING
                case 'static_norm':
                    reasoning_steps =  ONIONStaticNormal.NEGATIVE_ICL_REASONING
                case 'static_unfaithful':
                    reasoning_steps =  ONIONStaticUnfaithful.NEGATIVE_ICL_REASONING
                case 'static_unfaithful_reasoning':
                    reasoning_steps =  ONIONStaticUnfaithfulReasoning.NEGATIVE_ICL_REASONING
                case _:
                    raise ValueError(f"{atk_type} is not configured.")  
                
        return shuffle_reasoning_steps(reasoning_steps= reasoning_steps, plus_plus= plus_plus)
