from openai import OpenAI

client = OpenAI(
    base_url="http://100.106.117.77:8888/v1",
    api_key="sk-unsloth-bd7aa67e0bb1b869381ab043f784c7c0",
)

response = client.chat.completions.create(
    model="unsloth/Qwen3.5-9B-MTP-GGUF:UD-Q3_K_XL",
    messages=[{"role": "user", "content": "What is Unsloth?"}],
    stream=True,
)

for chunk in response:
    print(chunk.choices[0].delta.content or "", end="")