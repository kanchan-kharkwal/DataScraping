from bs4 import BeautifulSoup
import requests

url = "https://docs.snowflake.com/en/sql-reference/functions/upper"
html = requests.get(url).text

soup = BeautifulSoup(html, 'html.parser')
print(soup.find('h1').text)
print(soup.find('p').text)