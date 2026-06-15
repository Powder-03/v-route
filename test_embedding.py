import asyncio
from litellm import aembedding
import os

async def main():
    try:
        response = await aembedding(
            model="gemini/text-embedding-004", 
            input=["hello world"], 
            api_key=os.environ.get("GEMINI_API_KEY", "dummy")
        )
        print("Success:", response)
    except Exception as e:
        print("Error:", repr(e))

asyncio.run(main())
