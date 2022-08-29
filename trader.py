"""
Author: Razin S.
Email: razin@parsebox.net
"""
import os
import re  # I definitely wrote these regexes
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

# Cpu usage is insanely high on headless.
# TODO: Find a fix to high CPU usage


def logger(msg, log_file):
    time_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    with open(f'logs/{log_file}', 'a') as logs:
        msg = f'[{time_now}] {msg}'
        logs.writelines(f'{msg}\n')
        print(msg)


def get_driver() -> webdriver:
    options = Options()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/104.0.0.0 Safari/537.36")
    # options.add_argument("--headless")
    options.add_argument(f"user-data-dir={os.getcwd()}/chrome profile")
    options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
    # options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument("--start-maximized")
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
        time.sleep(random.choice([0.1, 0.2, 0.3]))


def check_win(web_driver: webdriver, trade_amount: int, log_file: str) -> bool:
    time.sleep(30)  # Wait before checking for win
    while True:  # Keep looking for the Popup
        time.sleep(1)
        try:
            return_amount = web_driver.find_element(
                By.XPATH, '//*[@id="trade"]/div/div/app-toasts/app-option-toast/div/span[3]').text.replace(',', '')
            return_amount = float(re.findall(r'([-+]*\d+\.\d+|[-+]*\d+)', return_amount)[0])

            msg = f'Returned: {return_amount}'
            logger(msg, log_file)

            try:
                web_driver.find_element(  # Close popup
                    By.XPATH, '//*[@id="trade"]/div/div/app-toasts/app-option-toast/div/button').click()
            except ElementClickInterceptedException:
                web_driver.find_element(By.XPATH, '/html/body/ng-component/vui-modal/div/div[1]/button').click()
                time.sleep(1)
                web_driver.find_element(  # Close popup
                    By.XPATH, '//*[@id="trade"]/div/div/app-toasts/app-option-toast/div/button').click()

            if return_amount > trade_amount:
                return True
            elif return_amount <= trade_amount:
                return False
        except NoSuchElementException:
            pass


def main(log_file, username: str, password: str, base_amount: int, martingale: float, martingale_stop: int,
         win_sleep: float, stop_balance: float):
    try:
        os.mkdir('logs')
    except FileExistsError:
        pass

    msg = 'Bot Started'
    logger(msg, log_file)

    amount_index = 0
    amounts = []
    for i in range(martingale_stop):
        amounts.append(str(int(base_amount)))
        base_amount *= martingale

    driver = get_driver()
    driver.get("https://binomo.com/trading")

    time.sleep(10)

    try:  # This block checks if we're asked to log in.
        login_text = driver.find_element(
            by='xpath', value='/html/body/binomo-root/lib-platform-scroll/div/div/div/ng-component/app-auth/div/div/p')
        if login_text.text == 'Login':
            msg = 'Session Expired: Attempting Login'
            logger(msg, log_file)

            driver.find_element(
                by='xpath',
                value='//*[@id="qa_auth_LoginEmailInput"]/vui-input/div[1]/div[1]/vui-input-text/input') \
                .send_keys(username)
            driver.find_element(
                by='xpath',
                value='//*[@id="qa_auth_LoginPasswordInput"]/vui-input/div[1]/div[1]/vui-input-password/input') \
                .send_keys(password)

            driver.find_element(by='xpath', value='//*[@id="qa_auth_LoginBtn"]/button').click()
            time.sleep(3)
            driver.refresh()

            msg = 'Logged In'
            logger(msg, log_file)

    except NoSuchElementException:  # Means we're already logged in
        try:  # Let Load
            WebDriverWait(driver, 40).until(
                expected_conditions.presence_of_element_located((By.XPATH, '//*[@id="qa_trading_balance"]')))
        except TimeoutException:
            msg = 'Timed Out - Exiting'
            logger(msg, log_file)
            driver.close()
            exit()

    try:  # Let Load
        WebDriverWait(driver, 40).until(
            expected_conditions.presence_of_element_located((By.XPATH, '//*[@id="qa_trading_balance"]')))
    except TimeoutException:
        msg = 'Timed Out - Exiting'
        logger(msg, log_file)
        driver.close()
        exit()

    msg = 'Started Trading'
    logger(msg, log_file)

    while True:
        try:
            balance = driver.find_element(By.ID, 'qa_trading_balance').text.replace(',', '')
            balance = float(re.findall(r'([-+]*\d+\.\d+|[-+]*\d+)', balance)[0])
            if balance >= stop_balance:
                msg = f'Balance Reached: {balance}'
                logger(msg, log_file)
                driver.close()
                exit()
            try:
                current_amount = amounts[amount_index]
            except IndexError:
                amount_index = 0
                current_amount = amounts[amount_index]

            time.sleep(2)  # Sometimes the bot captures the Opinion too fast.
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

            msg = f'New Trade: {current_trade} > {current_amount}'
            logger(msg, log_file)

            is_win = check_win(driver, int(current_amount), log_file)
            time.sleep(1)  # Wait for the Balance to Update after a trade is made
            balance = driver.find_element(By.ID, 'qa_trading_balance').text.replace(',', '')
            balance = float(re.findall(r'([-+]*\d+\.\d+|[-+]*\d+)', balance)[0])
            if is_win:
                msg = f'Win - Balance: {balance}'
                logger(msg, log_file)
                amount_index = 0
                time.sleep(win_sleep)
            else:
                msg = f'Loss - Balance: {balance}'
                logger(msg, log_file)
                amount_index += 1
        except ElementClickInterceptedException:  # Close Popups
            driver.find_element(By.XPATH, '/html/body/ng-component/vui-modal/div/div[1]/button').click()
            time.sleep(1)


if __name__ == '__main__':
    file = datetime.now().strftime("%d-%m-%Y %H-%M-%S") + '.txt'

    # Configuration
    user_name = str
    user_password = str
    base_trade_amount = float
    martingale_multiplier = float
    # Reset the martingale counter and start from base amount again
    max_martingale = int
    # Bot will sleep for specified number of seconds after every win
    win_wait = float
    # Bot will Pause itself after account balance reaches or goes over the specified amount
    exit_bal = float
 
    # user_name = input('Username: ')
    # user_password = input('Password: ')
    # base_trade_amount = float(input('Base Amount: '))
    # martingale_multiplier = float(input('Martingale Multiplier: '))
    # max_martingale = int(input('Martingale Stop: '))
    # win_wait = float(input('Win Sleep: '))  # Will pause for n number of seconds after each win
    # # Bot will Pause itself after account balance reaches or goes over the specified amount
    # exit_bal = float(input('Stop Balance: '))

    main(file, user_name, user_password, base_trade_amount, martingale_multiplier, max_martingale, win_wait, exit_bal)
