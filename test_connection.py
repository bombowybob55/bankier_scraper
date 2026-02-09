from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

# Konfiguracja dla przeglądarki Brave
chrome_options = Options()
chrome_options.binary_location = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"

# Automatyczne zarządzanie ChromeDriver
driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=chrome_options
)

# Test - otwórz Google
print("Otwieram stronę...")
driver.get("https://www.google.com")
time.sleep(3)
print("Test zakończony!")

driver.quit()
