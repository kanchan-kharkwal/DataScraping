import requests 

url ="https://docs.snowflake.com/en/sql-reference/functions/upper"
response = requests.get(url)

print(response.status_code)
# print(response.text) 
# print(response.headers)
print(response.content)