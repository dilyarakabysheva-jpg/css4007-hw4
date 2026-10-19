import json
import os
from openai import OpenAI
from lookup import calculate, lookup

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENAI_API_KEY"),
)

tools_map = {
    "lookup": lookup,
    "calculate": calculate
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "Searches active regional documents and correction notices by query string. Ignores ARCHIVED documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "District name (e.g. 'Brightwater') or topic (e.g. 'tariff')."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluates a string math expression safely and returns the numeric result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate, e.g. '44675 / 921.4'."
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

def run_react_agent(question: str, max_rounds: int = 8):
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert analytical assistant for the Nine Rivers region.\n"
                "1. Always use 'lookup' to get information. Search only simple terms like district names (e.g. 'Brightwater') or 'tariff'.\n"
                "2. Always use 'calculate' for math. NEVER do mental math.\n"
                "3. IMPORTANT: Once you call 'calculate' or get all document info, synthesize and write the final text answer immediately. Do not repeat tool calls."
            )
        },
        {"role": "user", "content": question}
    ]

    executed_calls = set()

    for round_num in range(max_rounds):
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages,
            tools=tools_schema,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        messages.append(response_message)

        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                call_id = tool_call.id
                
                call_key = f"{fn_name}:{json.dumps(fn_args, sort_keys=True)}"
                
                if call_key in executed_calls:
                    tool_output = "You already received the data/calculation for this call above. Write your final response to the user now without calling tools."
                else:
                    executed_calls.add(call_key)
                    tool_output = tools_map[fn_name](**fn_args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": str(tool_output)
                })
        else:
            return response_message.content

    # Запасной вызов, если закончились раунды
    final_res = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages + [{"role": "user", "content": "Please write the final concise answer now using the facts retrieved above."}]
    )
    return final_res.choices[0].message.content