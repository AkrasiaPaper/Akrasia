import os
from dotenv import load_dotenv
from openai import OpenAI
from utils.constants import CodeLLMUtils
from typing import List, Dict

load_dotenv()

O4_MINI = CodeLLMUtils.MODEL_NAMES['o4-mini']

class CodeLLM:
    def check_message_structure(self, messages: List[Dict[str, str]]) -> None:
        for d in messages:
            if not isinstance(d, dict):
                raise ValueError("Invalid message type.")
            if d['role'] not in ('user', 'assistant', 'system'):
                raise ValueError("Invalid message role.")

class OpenAIModel(CodeLLM):
    def __init__(self, model_name: str = O4_MINI) -> None:
        self.model_name = model_name
        api_key = os.getenv("OPEN_AI_API") 
        if model_name not in (CodeLLMUtils.MODEL_NAMES.values()):
            raise ValueError("Invalid OpenAI model name.")
        if not api_key:
            raise ValueError("OPENAI API key is missing.")
        
        self.client = OpenAI(api_key=api_key)

    def generate(self, messages: List[Dict[str, str]]) -> str:
        self.check_message_structure(messages=messages)

        response = self.client.chat.completions.create(
            model= self.model_name,
            messages=messages
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    m = OpenAIModel()
    messages = [{"role": "user", "content" : "tell me a fun fact"}]
    print(m.generate(messages))


    