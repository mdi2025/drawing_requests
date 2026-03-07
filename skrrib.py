from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# -----------------------
# Chrome setup (HEADLESS)
# -----------------------
options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 30)

try:
    # -----------------------
    # Open skribbl.io
    # -----------------------
    driver.get("https://skribbl.io/")
    print("Opened skribbl.io")

    # Enter name
    name_input = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "input-name")))
    name_input.clear()
    name_input.send_keys("hes")

    # Click play
    driver.find_element(By.CLASS_NAME, "button-play").click()
    print("Joined game")

    # Wait until game appears
    wait.until(EC.visibility_of_element_located((By.ID, "game")))

    # Wait until at least one player exists
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#game-players .players-list > div")) > 0)
    time.sleep(3)

    # -----------------------
    # Get players
    # -----------------------
    players = driver.find_elements(By.CSS_SELECTOR, "#game-players .players-list > div")

    print("\nPlayers in game:\n")
    my_player = None

    for p in players:
        lines = [x.strip() for x in p.text.split("\n") if x.strip()]
        if len(lines) >= 2:
            pname = lines[0]
            score = lines[1]
            print(f"{pname} - {score}")

        if "(You)" in p.text:
            my_player = p

    # -----------------------
    # Get invite link
    # -----------------------
    if my_player:
        driver.execute_script("arguments[0].click();", my_player)

        invite_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "modal-player-button-invite"))
        )

        driver.execute_script("arguments[0].click();", invite_btn)

        # Wait until the invite input gets a value
        wait.until(
            lambda d: d.find_element(By.ID, "input-invite").get_attribute("value") != ""
        )

        invite_link = driver.find_element(By.ID, "input-invite").get_attribute("value")
        print("\nInvite Link:", invite_link)

    else:
        print("Could not find your player.")

    time.sleep(20)

finally:
    driver.quit()