import json
import os
import pathlib
import pprint
import random
import time
import sys
import logging
import timeit
from urllib.parse import urlparse

import pyperclip

from typing import Optional, List
import html

from fp.fp import FreeProxy
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from webdriverdownloader import GeckoDriverDownloader
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import ProxyType
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains, Keys, Proxy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import Firefox, FirefoxOptions, FirefoxProfile

logger = logging.getLogger(__name__)

class BaseElement:
    def __init__(
            self,
            driver: webdriver,
            locate_by: str,
            locate_value: str,
            multiple: bool = False,
            wait_time: int = 100,
            optional: bool = False,
    ) -> None:

        self.driver = driver
        locator = (getattr(By, locate_by.upper(), "id"), locate_value)
        find_element = driver.find_elements if multiple else driver.find_element
        try:
            WebDriverWait(driver, wait_time).until(
                lambda driver: EC.element_to_be_clickable(locator)
            )
            self.element = find_element(*locator)
            return
        except Exception as er:
            if optional:
                self.element = None
                return
            logger.info(f"Exception :: {er}")
        except:
            if optional:
                self.element = None
                return
        print(f"Timed out trying to get element ({locate_by} = {locate_value})")
        logging.warning(f"Timed out trying to get element ({locate_by} = {locate_value})")
        logger.info("Closing browser")
        driver.quit()
        # sys.exit()


class Text(BaseElement):
    @property
    def text(self) -> str:
        if self.element is None:
            return ""

        return self.element.get_attribute("text")


class TextArea(BaseElement):
    def write(self, value: str, is_clipboard: bool = False) -> None:
        if self.element is None:
            return

        # Check OS to use Cmd or Ctrl keys
        cmd_ctrl = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL

        actions_handler = ActionChains(self.driver).move_to_element(self.element)
        actions_handler.click().key_down(cmd_ctrl).send_keys("a").key_up(cmd_ctrl).perform()
        actions_handler.send_keys(Keys.BACKSPACE).perform()
        actions_handler.send_keys(Keys.CLEAR).perform()
        if is_clipboard:
            # Copy the large text to the clipboard using pyperclip
            # xerox.copy(value)
            # klembord.set_text(value)
            # data =html.escape(value)
            # self.driver.execute_script(f"navigator.clipboard.writeText(unescape(`{data}`));")
            if os.getenv("MOZ_HEADLESS") is None:  # hidden browser
                pyperclip.copy(value)
            else:
                # BROWSERS_TYPE: str = os.getenv('BROWSERS_TYPE')
                # if 'firefox' == BROWSERS_TYPE.lower():
                #     pyautogui.write(value)
                time.sleep(max(float(len(value) / 1500), 5))
                self.driver.execute_script(f"navigator.clipboard.writeText(`{value}`);")  # app.jsx

            actions_handler.key_down(cmd_ctrl).send_keys('v').key_up(cmd_ctrl).perform()
        else:
            actions_handler.send_keys(*value).perform()

    @property
    def value(self) -> None:
        if self.element is None:
            return ""

        return self.element.get_attribute("value")


class Button(BaseElement):
    def click(self) -> None:
        if self.element is None:
            return

        try:
            can_click = getattr(self.element, "click", None)
            if callable(can_click):
                self.element.click()
        except:
            # Using javascript if usual click function does not work
            self.driver.execute_script("arguments[0].click();", self.element)
