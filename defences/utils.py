from dotenv import load_dotenv
import os
import time
from openai import OpenAI
from typing import Dict, List
from utils.constants import CodeLLMUtils
from anthropic import Anthropic
from anthropic.types import TextBlock
from google import genai
from google.genai import types
from google.genai.errors import ClientError
import re
import json
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

def clean_json_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()

def get_model_id(model:str):
    for key in CodeLLMUtils.MODEL_METADATA.keys():
        if model == key:
            return CodeLLMUtils.MODEL_METADATA[key]['id']
    else:
        raise ValueError(f"Invalid model used {model}")

def get_client(model: str):   
    if model == 'deepseek-v4-pro':
        return OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
    elif model in ['o3-mini', 'gpt-5']:
        return OpenAI(api_key=OPENAI_API_KEY)
    
    else:
        raise ValueError(f"Invalid model used {model}")


def run_inference(prompt_seq : List[Dict[str, str]]):
    MAX_RETRIES = 3
    lut_name = os.getenv("LUT_NAME") # Getting the name of the LLM under test
    lut_info = CodeLLMUtils.MODEL_METADATA[lut_name]
    model = lut_info['id']

    print(f"Model running: {model}")
    print(f"Model info: {lut_info}")

    trigger_phrase = None
    for i in range(MAX_RETRIES):
        if "claude" in model:
            # AWS Bedrock
            # client_anthropic = AnthropicBedrock(
            #     api_key=AWS_API_KEY,
            #     aws_region="us-east-1"
            # )
            client_anthropic = Anthropic(
                api_key=lut_info['api_key'],
            )
            try:
                response = client_anthropic.messages.create(
                    model=model,
                    max_tokens=8192,
                    messages=prompt_seq,
                    output_config={
                        "effort": lut_info['effort'],
                    },
                )
            except Exception as e:
                print(f"API call failed: {type(e).__name__}: {e}. Retrying (attempt {i + 1}/{MAX_RETRIES})...")
                continue

            trigger_phrase = None
            for i in range(len(response.content) - 1, -1, -1):
                item = response.content[i]
                if isinstance(item, TextBlock):
                    trigger_phrase = item.text.strip()
                    break

            if trigger_phrase is None:
                print("Something went wrong when generating the trigger from Anthropic AWS Bedrock. Try again")
                print(f"response content from the LLM: {response.content}")
                print(f"Retrying for the {i + 1}th")
            else:
                break
        elif "gemini" in model:
            
            client = genai.Client(project=lut_info['project_id'], enterprise=True, location="global")

            contents = []
            for msg in prompt_seq:
                role = msg["role"]
                gemini_role = "model" if role == "assistant" else "user"  # Gemini uses "model", not "assistant"
                contents.append(
                    types.Content(
                        role=gemini_role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )
            try: 
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        thinking_config=types.ThinkingConfig(
                            thinking_level=lut_info["effort"].upper()
                        )
                    )
                )
                trigger_phrase = response.text
                if trigger_phrase:
                    break  # success — exit the retry loop (this was missing before!)
            except ClientError as e:
                if getattr(e, 'code', None) == 429 or '429' in str(e):
                    delay = 10 * (2 ** i)  # exponential backoff: 10s, 20s, 40s, 80s...
                    print(f"Gemini rate-limited (429), retrying in {delay}s (attempt {i + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue
                else:
                    raise
            
            trigger_phrase = response.text
        else:

            client_openai = OpenAI(
                api_key=lut_info['api_key'],
                base_url=lut_info.get('base_url', None)
            )
            trigger_phrase = None

            try:
                response = client_openai.chat.completions.create(
                # model="anthropic/claude-3.7-sonnet:thinking",
                model=model,
                messages=prompt_seq,
                response_format={"type": "json_object"},
                # extra_body={"reasoning": {"enabled": True}},
                # max_tokens=200,
                # temperature=0.7
                reasoning_effort=lut_info['effort'],
                extra_body=lut_info.get('extra_body', None)
                )
            except Exception as e:
                print(f"API call failed: {type(e).__name__}: {e}. Retrying (attempt {i + 1}/{MAX_RETRIES})...")
                continue

            content = response.choices[0].message.content

            if content is None:
                print('Recieved None in LLM response. Retrying...')
                time.sleep(60)
                print("Sleeping for 60 seconds.")
                continue
            else:
                trigger_phrase = content.strip()  

            if trigger_phrase:
                print(f"Received a valid response from openai api: {trigger_phrase}")
                break
            else:
                print(f"Something went wrong, no response detected: {trigger_phrase}")
                print(f"Retrying for the {i + 1}th")

    return trigger_phrase

def extract_trigger(trigger_path: str) -> List:
    try:
        with open(trigger_path, 'r') as f:
            sample = json.loads(f.read().splitlines()[0])
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Trigger file not found: {trigger_path}") from e
    except (json.JSONDecodeError, IndexError) as e:
        raise ValueError(f"Could not parse trigger file {trigger_path}: {e}") from e

    triggers = sample.get("trigger", None)
    if not triggers:
        raise ValueError(f"No 'trigger' key found in {trigger_path}, sample was: {sample}")

    return triggers