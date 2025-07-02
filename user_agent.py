import random
import requests

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3)...",
    "Mozilla/5.0 (X11; Linux x86_64)..."
]

headers = {
    "User-Agent": random.choice(user_agents)
}
print(headers)

url = "https://docs.snowflake.com/en/sql-reference/sql/select"

response = requests.get(url, headers=headers)
print(response.status_code)

