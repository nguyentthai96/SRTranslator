import json
import os
import pathlib
import pprint
import random
import time
import sys
import logging
from urllib.parse import urlparse
from selenium_stealth import stealth
import pyperclip
from fake_useragent import UserAgent

from typing import Optional, List
import html

from fp.fp import FreeProxy
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
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
    if os.getenv("DISABLE_PROXY"): # have data or "1" return None as disable proxy
        return None

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
    """Creates a new Browser selenium webdriver. Install driver if not in path

    Args:
        proxy (Optional[Proxy], optional): Selenium WebDriver proxy. Defaults to None.

    Returns:
        WebDriver: Selenium WebDriver
    """

    # firefox -marionette -start-debugger-server 2828

    BROWSERS_TYPE: str = os.getenv('BROWSERS_TYPE')
    if 'firefox' == BROWSERS_TYPE.lower():
        pathProfile = 'FirefoxProfile'
        firefox_profile = pathlib.Path(pathProfile).resolve()

        service = webdriver.firefox.service.Service(
            # executable_path='/home/nguyentthai96/webdriver',
            # port=3000,
            service_args=[
                # '--marionette-port', '2828', '--connect-existing',
                '--log', 'debug',
                '--profile-root', pathProfile
            ],
            log_path='logs/selenium.log',
        )

        if not os.path.exists(firefox_profile):
            os.makedirs(firefox_profile)

        options = webdriver.FirefoxOptions()
        # only using profile.set_preference profile or options.add_argument
        options.add_argument("-profile")
        options.add_argument(pathProfile)

        #
        if os.getenv("MOZ_HEADLESS"):
            options.add_argument("-headless")

        # options.add_argument(f'user-agent={user_agent}')
        # options.set_preference("general.useragent.override", f'userAgent={user_agent}')
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
            driver = webdriver.Firefox(options=options, service=service)
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
            driver.execute("executeCdpCommand", {"cmd": "Browser.grantPermissions", "params": {
                "permissions": ["clipboardReadWrite", "backgroundSync", "backgroundFetch"]
            }})
        if logger.isEnabledFor(logging.DEBUG):
            driver.get("https://ifconfig.me")
            driver.save_screenshot("check_ip.png")
            agent = driver.execute_script("return navigator.userAgent;")
            profile_name = driver.capabilities.get('moz:profile').replace('\\', '/').split('/')[-1]
            logger.info("Profile name of Firefox running :: %s  agent %s", profile_name, agent)
        driver.maximize_window()
        return driver

    service = webdriver.chrome.service.Service(
        # executable_path=ChromeDriverManager().install(),
        service_args=[
            '--disable-build-check',
            # '--unsafely-treat-insecure-origin-as-secure=https://www.deepl.com' // allow get resource from enpoint not safe http
            '--append-log',
            '--readable-timestamp',
            '--log-level=DEBUG',
        ],
        log_path='./logs/selenium.log'
    )
    options = webdriver.ChromeOptions()
    if os.getenv("MOZ_HEADLESS"):
        options.add_argument('--headless')
    # options.binary_location = ChromeDriverManager().install()
    options.add_argument('--no-sandbox')
    #
    options.add_argument("--start-maximized")
    options.add_argument('window-size=1920x1080')
    options.add_argument('--disable-dev-shm-usage') # https://stackoverflow.com/questions/50642308/webdriverexception-unknown-error-devtoolsactiveport-file-doesnt-exist-while-t
    options.add_argument('disable-gpu')
    #
    # options.add_argument("--remote-debugging-port=9222")
    options.add_argument('user-data-dir=./ChromeProfile')

    options.add_argument("--enable-javascript")
    options.add_argument("start-maximized")
    #
    options.add_experimental_option("detach", True)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-user-media-security=true")
    options.add_argument("--disable-blink-features=AutomationControlled")

    ua = UserAgent() # from fake_useragent import UserAgent
    user_agent = ua.random
    options.add_argument(f'user-agent={user_agent}')

    try:
        logger.info("Creating Selenium Webdriver instance")
        driver = webdriver.Chrome(options=options, service=service)
    except WebDriverException as e:
        logger.info("Installing Driver cause it isn't installed")
        logging.exception("WebDriverException", e, stack_info=True)
        ChromeDriverManager().install()
        driver = webdriver.Chrome(options=options, service=service)
    if logger.isEnabledFor(logging.DEBUG):
        driver.get("https://ifconfig.me")
        driver.save_screenshot("check_ip.png")
        agent = driver.execute_script("return navigator.userAgent;")
        logger.info("Profile name of Chrome running ::  agent %s", agent)

    # https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec/53040904#53040904
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
    driver.execute_cdp_cmd("Browser.grantPermissions", {
        "permissions": ["clipboardReadWrite", "backgroundSync", "backgroundFetch"]
    })
    #
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
    driver.maximize_window()
    return driver
