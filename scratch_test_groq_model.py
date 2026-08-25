import openai
from platform_core.config import settings

client = openai.OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
resp = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": 'Respond in JSON: {"status": "success"}'}]
)
print("Groq response:", resp.choices[0].message.content)
