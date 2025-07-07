import requests
from bs4 import BeautifulSoup

url = "https://docs.snowflake.com/en/sql-reference/functions/upper"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Extract function name (h1)
function_name = soup.find("h1").text.strip()

# Extract first paragraph after h1 (function description)
description = soup.find("div", class_="topic-content").text.strip()

# Extract all code blocks
code_blocks = soup.find_all("pre")
code_examples = [cb.text.strip() for cb in code_blocks]

print(f"Function: {function_name}")
print(f"Description: {description}")
print("\n--- Syntax & Examples ---")
for code in code_examples:
    print(code)
    print("-----------------------")
