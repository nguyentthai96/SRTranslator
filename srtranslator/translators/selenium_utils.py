import json
import os
import pathlib
import pprint
import random
import time
import sys
import logging
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


def create_proxy(country_id: Optional[List[str]] = ["US"],
                 proxyAddresses: Optional[List[str]] = None) -> Optional:
    """Creates a new proxy to use with a selenium driver and avoid get banned

    Args:
        country_id (Optional[List[str]], optional): Contry id to create proxy. Defaults to ['US'].
        proxyAddresses (Optional[List[str]], optional): list address proxy.

    Returns:
        Proxy: Selenium WebDriver proxy
    """

    if proxyAddresses is None:
        logger.info("Getting a new Proxy from https://www.sslproxies.org/")
        address = FreeProxy(country_id=country_id, https=True).get()
        parse = urlparse(address)
        proxyAddress = f"{parse.hostname}:{parse.port}"
    else:
        proxyAddress = random.choice(proxyAddresses)

    [proxyHost, proxyPort] = proxyAddress.split(":")

    return dict(
        proxyAddress=proxyAddress,
        proxyHost=proxyHost,
        proxyPort=int(proxyPort)
    )


def create_driver(proxy: Optional = None) -> WebDriver:
    """Creates a new Firefox selenium webdriver. Install geckodriver if not in path

    Args:
        proxy (Optional[Proxy], optional): Selenium WebDriver proxy. Defaults to None.

    Returns:
        WebDriver: Selenium WebDriver
    """
    service = Service(log_path='tmp/selenium.log', service_args=[
        '--log', 'debug',
        '--profile-root', 'tmp'
    ])
    options = webdriver.FirefoxOptions()
    # only using profile.set_preference profile or options.add_argument
    options.add_argument("-profile")
    options.add_argument('tmp/firefox_profile')
    #
    options.add_argument("-headless")
    #
    # firefox_profile = FirefoxProfile()
    # firefox_profile.set_preference('profile', 'tmp/firefox_profile')
    # firefox_profile.set_preference("javascript.enabled", True)
    # options.profile = firefox_profile

    if proxy is not None:
        logger.info("Connect with proxy address :: %s", proxy['proxyAddress'])
        # webdriver.DesiredCapabilities.FIREFOX['proxy'] = Proxy(
        #     dict(
        #         proxyType=ProxyType.MANUAL,
        #         httpProxy=proxy['proxyAddress'],
        #         ftpProxy=proxy['proxyAddress'],
        #         sslProxy=proxy['proxyAddress'],
        #         noProxy="",
        #     )
        # )
        # https://stackoverflow.com/questions/42335857/python-selenium-firefox-proxy-does-not-work
        # # Direct = 0, Manual = 1, PAC = 2, AUTODETECT = 4, SYSTEM = 5
        options.set_preference("network.proxy.type", 1)
        options.set_preference("network.proxy.http", proxy['proxyHost'])
        options.set_preference("network.proxy.httpProxyAll", True)
        options.set_preference("network.proxy.http_port", proxy['proxyPort'])
        # options.set_preference("network.proxy.https", proxy['proxyHost'])
        # options.set_preference("network.proxy.https_port", proxy['proxyPort'])
        options.set_preference("network.proxy.share_proxy_settings", True)
        options.set_preference("network.proxy.ssl", proxy['proxyHost'])
        options.set_preference("network.proxy.ssl_port", proxy['proxyPort'])
        options.set_preference("network.proxy.socks", proxy['proxyHost'])
        options.set_preference("network.proxy.socks_port", proxy['proxyPort'])
        options.set_preference("network.proxy.socks_version", 5)
        # no use cannot access page
        options.set_preference('network.proxy.socks_remote_dns', False)
        options.set_preference('network.proxy.proxyDNS', False)
        options.set_preference("network.http.use-cache", False)
    else:
        options.set_preference("network.proxy.type", 4)

    logger.info("Creating Selenium Webdriver instance")
    try:
        # service = Service(port=3000, service_args=[
        #     '--marionette-port', '2828', '--connect-existing',
        #     '--log', 'debug',
        #     '--profile-root', 'tmp'
        # ])
        #
        driver = webdriver.Firefox(options=options, service=service)
        driver.get("https://ifconfig.me")
        driver.save_screenshot("check_ip.png")
    except WebDriverException as e:
        logger.info("Installing Firefox GeckoDriver cause it isn't installed")
        logging.exception("WebDriverException", e)
        gdd = GeckoDriverDownloader()
        gdd.download_and_install()

        # C:\Users\<UserName>\AppData\Roaming.
        # https://www.browserstack.com/automate/capabilities
        # https://stackoverflow.com/questions/72331816/how-to-connect-to-an-existing-firefox-instance-using-seleniumpython
        # https://www.minitool.com/news/your-firefox-profile-cannot-be-loaded.html
        # firefox -p
        # firefox.exe --new-instance -ProfileManager -marionette -start-debugger-server 2828
        # firefox.exe -marionette -start-debugger-server 2828
        # firefox.exe --new-instance -P deepl -marionette
        # service = Service(port=3000, service_args=['--marionette-port', '2828', '--connect-existing'])
        # https://github.com/aiworkplace/Selenium-Project
        driver = webdriver.Firefox(options=options, service=service)

    profile_name = driver.capabilities.get('moz:profile').replace('\\', '/').split('/')[-1]
    logger.info("Profile name of Firefox running :: %s", profile_name)
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
            logger.info("Closing browser")
            driver.quit()
            sys.exit()


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
            # pyperclip.copy(value)
            # xerox.copy(value)
            # klembord.set_text(value)
            # data =html.escape(value)
            # self.driver.execute_script(f"navigator.clipboard.writeText(unescape(`{data}`));")
            self.driver.execute_script(f"navigator.clipboard.writeText(`{value}`);")
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
