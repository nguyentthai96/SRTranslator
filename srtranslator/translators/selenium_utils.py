import time
import sys
import logging
import pyperclip
from typing import Optional, List
from fp.fp import FreeProxy
from selenium import webdriver
from webdriverdownloader import GeckoDriverDownloader
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver import Firefox, FirefoxOptions, FirefoxProfile


logger = logging.getLogger(__name__)
def create_proxy(country_id: Optional[List[str]] = ["US"]) -> Proxy:
    """Creates a new proxy to use with a selenium driver and avoid get banned

    Args:
        country_id (Optional[List[str]], optional): Contry id to create proxy. Defaults to ['US'].

    Returns:
        Proxy: Selenium WebDriver proxy
    """
    logging.info("Getting a new Proxy from https://www.sslproxies.org/")
    proxy = FreeProxy(country_id=country_id).get()
    # proxy = Proxy(
    #     dict(
    #         proxyType=ProxyType.MANUAL,
    #         httpProxy=proxy,
    #         ftpProxy=proxy,
    #         sslProxy=proxy,
    #         noProxy="",
    #     )
    # )

    return proxy


def create_driver(proxy: Optional[Proxy] = None) -> WebDriver:
    """Creates a new Firefox selenium webdriver. Install geckodriver if not in path

    Args:
        proxy (Optional[Proxy], optional): Selenium WebDriver proxy. Defaults to None.

    Returns:
        WebDriver: Selenium WebDriver
    """
    logging.info("Creating Selenium Webdriver instance")
    try:
        # service = Service(executable_path='/home/nguyentthai96/webdriver',  port=3000, service_args=['--marionette-port', '2828', '--connect-existing'])
        #
        # opts=Options()
        opts = webdriver.FirefoxOptions()
        if proxy:
            opts.add_argument(f'--proxy-server={proxy}')
        opts.add_argument("-headless")
        opts.headless = True
        opts.profile = FirefoxProfile(profile_directory='firefox_profile')
        # profile = webdriver.FirefoxProfile('/home/nguyentthai96/Desktop/freelancer/SRTranslator/examples/firefox_profile')
        # profile = webdriver.FirefoxProfile(profile_directory="/home/nguyentthai96/Desktop/freelancer/SRTranslator/examples/firefox_profile")
        # opts.set_preference("profile", "/home/nguyentthai96/Desktop/freelancer/SRTranslator/examples/firefox_profile")
        # opts.profile = FirefoxProfile("/home/nguyentthai96/Desktop/freelancer/SRTranslator/examples/firefox_profile")
        # opts.add_argument("-profile")
        # opts.add_argument("/home/nguyentthai96/Desktop/freelancer/SRTranslator/examples/firefox_profile")
        # opts.add_argument('--user-data-dir=/home/nguyentthai96/Desktop/freelancer/SRTranslator/examples/firefox_profile')

        # opts.add_argument('--headless')
        # opts.profile = FirefoxProfile("/home/nguyentthai96/Desktop/freelancer/SRTranslator/examples/firefox_profile")

        # driver = webdriver.Firefox()
        driver = webdriver.Firefox(options=opts)
        # driver = webdriver.Firefox(options=opts, service=service)

    except WebDriverException as e:
        # logging.exception("WebDriverException", e, exc_info=True)
        logging.info("Installing Firefox GeckoDriver cause it isn't installed")
        gdd = GeckoDriverDownloader()
        gdd.download_and_install()

        # firefox -marionette -start-debugger-server 2828
        # service = Service(port=3000, service_args=['--marionette-port', '2828', '--connect-existing'])
        driver = webdriver.Firefox()

    driver.maximize_window()
    return driver


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
        except:
            if optional:
                self.element = None
                return

            print(f"Timed out trying to get element ({locate_by} = {locate_value})")
            logging.warning(f"Timed out trying to get element ({locate_by} = {locate_value})")
            logging.info("Closing browser")
            driver.quit()
            sys.exit()


class Text(BaseElement):
    @property
    def text(self) -> str:
        if self.element is None:
            return ""

        return self.element.get_attribute("text")


class TextArea(BaseElement):
    def write(self, value: str, is_clipboard:bool) -> None:
        if self.element is None:
            return

        # Check OS to use Cmd or Ctrl keys
        cmd_ctrl = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL

        actions_handler = ActionChains(self.driver).move_to_element(self.element)
        # time.sleep(4)
        # logging.info("cmd_ctrl A...............................................")
        actions_handler.click().key_down(cmd_ctrl).send_keys("a").key_up(cmd_ctrl).perform()
        # logging.info("cmd_ctrl CLEAR...............................................")
        # time.sleep(4)
        actions_handler.send_keys(Keys.BACKSPACE).perform()
        # logging.info("cmd_ctrl BACKSPACE...............................................")
        # time.sleep(4)
        actions_handler.send_keys(Keys.CLEAR).perform()
        # time.sleep(5)
        # logging.info(f"Clearing............................................... {is_clipboard}")
        if (is_clipboard) :
            # Copy the large text to the clipboard using pyperclip
            pyperclip.copy(value)
            # logging.info("cmd_ctrl VVVVVVVV...............................................", *value)
            # time.sleep(5)
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
