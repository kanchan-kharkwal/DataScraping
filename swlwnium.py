from selenium import webdriver
from selenium.webdriver.common.by import By
import time

# Setup driver
driver = webdriver.Chrome()

# Load a Snowflake function documentation page
url = "https://docs.snowflake.com/en/sql-reference/functions/upper"
driver.get(url)

# Allow JS to load
time.sleep(3)

print(driver.title)
# Find the search box, enter a query, submit
search_box = driver.find_element(By.NAME, "q")

time.sleep(3)
print(driver.title)

driver.quit()
