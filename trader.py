"""
Author: Razin S.
Email: razin@parsebox.net
"""
import os
import re  # I definitely wrote these regexes
import time
import random
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def get_driver() -> webdriver:
    options = Options()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/104.0.0.0 Safari/537.36")
    options.add_argument("--start-maximized")

    # TODO: Add Headless Mode and Fix check_win in headless mode
    # Headless does work on typing and making trades but check_win failed on my test.
    # options.add_argument("--headless")

    options.add_argument(f"user-data-dir={os.getcwd()}/chrome profile")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument('--log-level=3')

    s = Service('chromedriver.exe')
    return webdriver.Chrome(service=s, options=options)


def enter_amount(web_driver: webdriver, amount: str):
    amount_element = web_driver.find_element(By.XPATH, '//*[@id="amount-counter"]/div[1]/div[1]/vui-input-number/input')
    amount_element.send_keys(Keys.CONTROL + 'A', Keys.BACKSPACE)
    for character in amount:
        amount_element.send_keys(character)
        time.sleep(random.choice([0.2, 0.3, 0.5]))


def check_win(web_driver: webdriver, trade_amount: int) -> bool:
    while True:  # Keep looking for the Popup
        try:
            return_amount = web_driver.find_element(
                By.XPATH, '//*[@id="trade"]/div/div/app-toasts/app-option-toast/div/span[3]').text
            return_amount = float(re.findall(r'([-+]*\d+\.\d+|[-+]*\d+)', return_amount)[0])
            if return_amount > trade_amount:
                web_driver.find_element(  # Close the popup
                    By.XPATH, '//*[@id="trade"]/div/div/app-toasts/app-option-toast/div/button').click()
                return True
            elif return_amount <= trade_amount:
                web_driver.find_element(  # Close the popup
                    By.XPATH, '//*[@id="trade"]/div/div/app-toasts/app-option-toast/div/button').click()
                return False
        except NoSuchElementException:
            pass


def main():
    # Configuration
    base_amount = float(input('Base Amount: '))
    martingale = float(input('Martingale Multiplier: '))
    martingale_stop = int(input('Martingale Stop: '))  # Reset the martingale counter and start from base amount again
    win_sleep = float(input('Win Sleep: '))  # Will pause for n number of seconds after each win
    # Bot will Pause itself after account balance reaches or goes over the specified amount
    stop_balance = float(input('Stop Balance: '))

    amount_index = 0
    amounts = []
    for i in range(martingale_stop):
        amounts.append(str(int(base_amount)))
        base_amount *= martingale

    driver = get_driver()
    driver.get("https://binomo.com/trading")

    time.sleep(5)
    input('\aPress Enter To Start Trading: ')
    while True:
        try:
            balance = driver.find_element(By.ID, 'qa_trading_balance').text.replace(',', '')
            balance = float(re.findall(r'([-+]*\d+\.\d+|[-+]*\d+)', balance)[0])
            if balance >= stop_balance:
                print('Balance Reached: ', balance)
                input('Press Enter To Run Again\nOr CTRL+C To Quit: ')
                base_amount = float(input('Base Amount: '))
                martingale = float(input('Martingale Multiplier: '))
                martingale_stop = int(input('Martingale Stop: '))
                win_sleep = float(input('Win Sleep: '))
                stop_balance = float(input('Stop Balance: '))

                amount_index = 0
                amounts = []
                for i in range(martingale_stop):
                    amounts.append(str(int(base_amount)))
                    base_amount *= martingale

            try:
                current_amount = amounts[amount_index]
            except IndexError:
                amount_index = 0
                current_amount = amounts[amount_index]

            time.sleep(1)  # Sometimes the bot captures the Opinion too fast.
            call_opinion = driver.find_element(
                By.XPATH, '//*[@id="trade-menu"]/majority-opinion/div/div/div[2]/span[1]').text.replace('%', '').strip()
            call_button = driver.find_element(By.XPATH, '//*[@id="qa_trading_dealUpButton"]/button')
            put_button = driver.find_element(By.XPATH, '//*[@id="qa_trading_dealDownButton"]/button')

            if int(call_opinion) > 50:  # Majority Favours The Direction "UP"
                enter_amount(driver, current_amount)
                call_button.click()
                current_trade = 'Call'

            elif int(call_opinion) < 50:  # Majority Favours The Direction "Down"
                enter_amount(driver, current_amount)
                put_button.click()
                current_trade = 'Put'

            else:  # Market Opinion Is Neutral
                enter_amount(driver, current_amount)
                # Randomly Make A Trade
                if random.choice(['call', 'put']) == 'call':
                    call_button.click()
                    current_trade = 'Call'
                else:
                    put_button.click()
                    current_trade = 'Put'

            time.sleep(1)  # Wait for the Balance to Update after a trade is made
            balance = driver.find_element(By.ID, 'qa_trading_balance').text.replace(',', '')
            balance = float(re.findall(r'([-+]*\d+\.\d+|[-+]*\d+)', balance)[0])
            print(f'New Trade: {current_trade} > {current_amount}\nBalance: {balance}')

            is_win = check_win(driver, int(current_amount))
            if is_win:
                print('Win - ', end='')
                amount_index = 0
                time.sleep(win_sleep)
            else:
                print('Loss - ', end='')
                amount_index += 1
        except ElementClickInterceptedException:  # Close Popups
            driver.find_element(By.XPATH, '/html/body/ng-component/vui-modal/div/div[1]/button').click()
            time.sleep(1)


if __name__ == '__main__':
    main()
