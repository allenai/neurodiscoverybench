import json

import time

from openai import OpenAI

from tenacity import (
    retry,
    stop_after_attempt,  # type: ignore
    wait_random_exponential,  # type: ignore
)

OPENAI_GEN_HYP = {
    "temperature": 0,
    "max_tokens": 250,
    "top_p": 1.0,
    "frequency_penalty": 0,
    "presence_penalty": 0,
}

DEFAULT_EVAL_OPENAI_MODEL = "gpt-4o-2024-08-06"


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def run_chatgpt_query_multi_turn(
    messages,
    model_name="gpt-4-turbo",  # pass "gpt4" for more recent model output
    max_tokens=256,
    temperature=0.0,
    json_response=False,
):
    response = None
    num_retries = 3
    retry = 0
    while retry < num_retries:
        retry += 1
        try:
            client = OpenAI()

            if json_response:
                response = client.chat.completions.create(
                    model=model_name,
                    response_format={"type": "json_object"},
                    messages=messages,
                    **OPENAI_GEN_HYP,
                )
            else:
                response = client.chat.completions.create(
                    model=model_name, messages=messages, **OPENAI_GEN_HYP
                )
            break

        except Exception as e:
            print(e)
            print("GPT error. Retrying in 2 seconds...")
            time.sleep(2)

    return response


def create_prompt(usr_msg):
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant who is not talkative. You only respond with the exact answer to a query without additional conversation.",
        },
        {"role": "user", "content": usr_msg},
    ]


def get_response(client, prompt, max_retry=5, model="gpt-3.5-turbo", verbose=False):
    n_try = 0
    while n_try < max_retry:
        response = client.chat.completions.create(
            model=model, messages=create_prompt(prompt), **OPENAI_GEN_HYP
        )
        output = (
            response.choices[0].message.content.strip().strip("```json").strip("```")
        )
        try:
            response_json = json.loads(output)
            return response_json
        except ValueError:
            if verbose:
                print(f"Bad JSON output:\n\n{output}")
            n_try += 1
            if n_try < max_retry:
                if verbose:
                    print("Retrying...")
            else:
                if verbose:
                    print("Retry limit reached")
    return None
