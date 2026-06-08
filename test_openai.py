import os
from openai import OpenAI

try:
    client = OpenAI(
        base_url="http://100.115.235.43:8081/v1",
        api_key="fake-key",
        max_retries=0,
    )
    print("Connecting...")
    res = client.models.list()
    print("Success:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
