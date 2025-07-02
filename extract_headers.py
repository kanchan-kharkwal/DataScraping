import requests
from bs4 import BeautifulSoup

url = "https://docs.snowflake.com/en/sql-reference/sql/select"
headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# Extract page title
title = soup.find("title").text
print("Title:", title)

# Extract all section headings
headings = soup.find_all(["h1", "h2", "h3"])
for h in headings:
    print(h.name, "-", h.text.strip())

# Extract paragraphs
paragraphs = soup.find_all("p")
for p in paragraphs[:5]:  
    print(p.text.strip())
