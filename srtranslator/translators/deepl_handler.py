import os
import time
import logging
import timeit

from typing import Optional, List

from selenium.webdriver import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from selenium.webdriver.common.by import By
from .base import Translator, TimeOutException
from .selenium_utils import (
    create_proxy,
    create_driver,
)
from .selenium_components import (
    TextArea,
    Button,
    Text, BaseElement,
)

logger = logging.getLogger(__name__)


class DeeplTranslator(Translator):
    url = "https://www.deepl.com/translator"
    max_char = 3000
    proxy_address: List[str] = None
    languages = {
        "auto": "Any language (detect)",
        "bg": "Bulgarian",
        "zh": "Chinese",
        "cs": "Czech",
        "da": "Danish",
        "nl": "Dutch",
        "en": "English",  # Only usable for source language
        "en-US": "English (American)",  # Only usable for destination language
        "en-GB": "English (British)",  # Only usable for destination language
        "et": "Estonian",
        "fi": "Finnish",
        "fr": "French",
        "de": "German",
        "el": "Greek",
        "hu": "Hungarian",
        "id": "Indonesian",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "lv": "Latvian",
        "lt": "Lithuanian",
        "pl": "Polish",
        "pt": "Portuguese",  # Only usable for source language
        "pt-PT": "Portuguese",  # Only usable for destination language
        "pt-BR": "Portuguese (Brazilian)",  # Only usable for destination language
        "ro": "Romanian",
        "ru": "Russian",
        "sk": "Slovak",
        "sl": "Slovenian",
        "es": "Spanish",
        "sv": "Swedish",
        "tr": "Turkish",
        "uk": "Ukrainian",
    }

    def __init__(self, driver: Optional[WebDriver] = None, username: str = None, password: str = None):
        self.username = username
        self.password = password
        self.last_translation_failed = False  # last_translation_failed is False still stop drive and retry proxy new, try proxy still failed is True
        self.driver = driver

        if self.driver is None:
            self._rotate_proxy()
            return

        self._reset()

    def _reset(self):
        logger.info(f"Going to {self.url}")
        self.driver.get(self.url)
        #
        if os.getenv("LOGIN_AUTO"):
            try:
                self._set_login(self.username, self.password)
            except Exception as e:
                logger.exception(f"Error exception login :: error ", e)

        self._closePopUp()

        self.input_lang_from = TextArea(
            self.driver, "XPATH", f"//d-textarea[@data-testid='translator-source-input']"
            # @data-testid='translator-source-input'  @aria-labelledby='translation-source-heading'
        )
        self.input_destination_language = TextArea(
            self.driver, "XPATH", f"//d-textarea[@data-testid='translator-target-input']"
        )

        self.src_lang = None
        self.target_lang = None

    def _rotate_proxy(self):
        if self.driver is not None:
            logger.warning(" ======= Translation failed. Probably got banned. ======= ")
            logger.info("Rotating proxy")
            self.quit()

        proxy = create_proxy(proxyAddresses=self.proxy_address)
        self.driver = create_driver(proxy)
        self._reset()

    def _closePopUp(self):
        Button(
            self.driver,
            "CSS_SELECTOR",
            "[aria-label=Close]",
            # wait_time=50,
            optional=True,
        ).click()

    def _set_source_language(self, language: str) -> None:
        self._set_language(language, "//button[@data-testid='translator-source-lang-btn']")
        self.src_lang = language

    def _set_destination_language(self, language: str) -> None:
        self._set_language(language, "//button[@data-testid='translator-target-lang-btn']")
        self.target_lang = language

    def _set_language(self, language: str, dropdown_class: str) -> None:
        # Click the languages dropdown button
        Button(self.driver, "XPATH", dropdown_class).click()

        # Get the language button to click based on is dl-test property or the text in the button
        xpath_by_property = (
            f"//button[@data-testid='translator-lang-option-{language}']"
        )
        x_path_by_text = f"//button[text()='{self.languages[language]}']"
        xpath = f"{xpath_by_property} | {x_path_by_text}"

        # Click the wanted language button
        Button(self.driver, "XPATH", xpath).click()

    def _check_user_session_default(self):
        try:
            # find_element = self.driver.find_elements if multiple else self.driver.find_element Text
            # self.element = find_element((By.XPATH, f"//div[@class='dl_header_menu_v2__buttons__emailName_container']"))
            user_logged = Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-in-btn']//span",
                                 multiple=True, optional=True)

            if user_logged and user_logged.element:
                els = user_logged.element
                if len(els) > 1:
                    self.username_current = els[1].text
                    self.user_session_view = els[1]
                else:
                    self.username_current = els[0].text
                    self.user_session_view = els[0]

            else:
                self.username_current = None
        except:
            logger.error("Checking login failed, next check firefox.")
            self.username_current = None

        BROWSERS_TYPE: str = os.getenv('BROWSERS_TYPE')
        if self.username_current is None or 'firefox' == BROWSERS_TYPE.lower():
            logger.info("Try more check user session with firefox.")
            self._check_user_session_firefox()

    def _check_user_session_firefox(self):
        try:
            # find_element = self.driver.find_elements if multiple else self.driver.find_element Text
            # self.element = find_element((By.XPATH, f"//div[@class='dl_header_menu_v2__buttons__emailName_container']"))
            self.user_session_view = Button(self.driver, "XPATH", f"//button[@id='usernav-button']", optional=True)
            self.user_session_view.click()
            time.sleep(1)
            user_logged = Text(self.driver, "XPATH",
                               # f"//nav[@aria-labelledby='usernav-button']//div[@class='user-item']//section[@aria-labelledby='userItemUserInfo']",
                               f"//h2[@id='userItemUserInfo']/parent::section//div",
                               multiple=True,
                               optional=True)

            if user_logged and user_logged.element:
                els = user_logged.element
                if len(els) > 1:
                    self.username_current = els[1].text
                    self.user_session_view = els[1]
                else:
                    self.username_current = els[0].text
                    self.user_session_view = els[0]
            else:
                self.username_current = None
            time.sleep(1)
            self._closePopUp()
            time.sleep(1)
        except:
            logger.error("Checking login firefox failed.")
            self.username_current = None

    def _logout_user_session(self):
        self.user_session_view.click()  # view popup button avatar
        time.sleep(3)
        labelLogout = "Log out"
        xpath_by_property = f"//nav[@aria-labelledby='usernav-button']//ul[@class='list-none']//span[contains(text(),'{labelLogout}')]"
        x_path_by_text = f"//nav[@aria-labelledby='usernav-button']//span[text()='Log out']"
        x_path_by_text = f"//nav[@aria-labelledby='usernav-button']//span[text()='Log out']"
        btnLogout = Button(self.driver, "XPATH",
                           f"{xpath_by_property} | {x_path_by_text} | //button[@data-testid='menu-account-logout']",
                           optional=True)
        if btnLogout and btnLogout.element:
            logger.info("Logout on firefox....")
        else:
            btnLogout = Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-logout']", optional=True)

        btnLogout.click()  # self.driver.execute_script('$(`[data-testid="menu-account-logout"]`).click()')
        time.sleep(5)
        self._closePopUp()

    def _set_login(self, username: str, password: str) -> None:
        time.sleep(6)
        logger.info("Checking login username.")
        self.user_session_view = None

        self._check_user_session_default()

        logger.info(f"Username current login :: {self.username_current}")
        if self.username_current is not None and (
                len(self.username_current) > 0 > self.username_current.find(username)):  # login others
            logger.info(f"Username existed user current logged {self.username_current}, need logout that.")
            self._logout_user_session()
        elif self.username_current is not None and (
                len(self.username_current) > 0 and self.username_current.find(username) >= 0):  # login same
            return

        self._login_user_session_new(username, password)

        #
        notification = BaseElement(self.driver, "XPATH", f"//div[@data-testid='error-notification']", optional=True)
        if notification.element:
            logger.error(f"Check login status :: {notification.element.text}")
            logger.error(f"==========================================================================================")
        else:
            time.sleep(8)

            self._check_user_session_default()
            logger.info(f"Now login with username :: {self.username_current}")

    def _is_translated(self, original: str, translation: str) -> bool:
        if (
                len(translation) != 0
                and len(original.splitlines()) == len(translation.splitlines())
                and original != translation
        ):
            return True
        else:
            logger.info(
                f"not _is_translated splitlines {len(original.splitlines()) == len(translation.splitlines())}   {len(original.splitlines())} {len(translation.splitlines())}")
            return False

    def translate(self, text: str, source_language: str, destination_language: str):
        start = timeit.default_timer()

        try:
            start = timeit.default_timer()
            if source_language != self.src_lang:
                self._set_source_language(source_language)
            if destination_language != self.target_lang:
                self._set_destination_language(destination_language)

            if logger.isEnabledFor(
                    logging.NOTSET):  # https://stackoverflow.com/questions/42900214/how-to-download-a-html-webpage-using-selenium-with-python
                self.driver.save_screenshot(f"{self.src_lang}_{self.target_lang}_{start}_____pre_progress__.png")
                with open(f"{self.src_lang}_{self.target_lang}_{start}_____pre_progress__.html", "w",
                          encoding='utf-8') as f:
                    f.write(self.driver.page_source)
            self.input_lang_from.write(value=(text), is_clipboard=True)
            if (self.input_lang_from.value is not None
                    and len(text.split("\n\n")) != len(
                        str(self.input_lang_from.value)
                                                               .split('\n\n'))
            ):
                self.input_lang_from.write(value=(text), is_clipboard=True)
            logger.debug(f"TIME SET :: {start} source {timeit.default_timer() - start}")
        except Exception as e:
            logger.warning("Error catch exception element.........................................................", e)

        try:
            time.sleep(4)
            for j in range(10):
                progress = BaseElement(self.driver, "XPATH", f"//*[@id='translator-progress-description']",
                                       optional=True)
                if logger.isEnabledFor(logging.NOTSET):
                    self.driver.save_screenshot(f"{self.src_lang}_{self.target_lang}_{start}___progress_{j}.png")
                    with open(f"{self.src_lang}_{self.target_lang}_{start}____progress_{j}.html", "w",
                              encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                time.sleep(1)
                if progress and progress.element:
                    time.sleep(2)
                    logger.info(f"*** {progress.element.text}")
                if progress is None:
                    break
        except:
            pass

        if logger.isEnabledFor(logging.NOTSET):
            self.driver.save_screenshot(f"{self.src_lang}_{self.target_lang}_{start}_after_waiting.png")
            with open(f"{self.src_lang}_{self.target_lang}_{start}_after_waiting.html", "w", encoding='utf-8') as f:
                f.write(self.driver.page_source)

        for _ in range(5):
            try:
                translation = str(self.input_destination_language.value)
                logger.info(
                    f"{timeit.default_timer()} - {start} :: translation output :: [{_}] :: input {len(text)} :: translation {len(translation)}")

                if self._is_translated(text, translation):
                    # Reset the proxy flag -- is success - last not failed
                    self.last_translation_failed = False
                    try:
                        time.sleep(2)
                        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.CONTROL + Keys.HOME)
                    except:
                        logger.info("Exception throw scroll by HOME")
                    return translation

                time.sleep(2)
            except Exception as e:
                logger.warning("Error catch exception.............................................................", e)

        # Maybe proxy got banned, so we try with a new proxy, but just once.
        if not self.last_translation_failed:  # failing, see_ing default is failing but first time not failed
            self.last_translation_failed = True
            self._rotate_proxy()
            return self.translate(text, source_language, destination_language)

        self.quit()
        raise TimeOutException("Translation timed out - Had try proxy but still failed.")

    def quit(self):
        self.driver.quit()

    def _login_user_session_new(self, username: str, password: str):
        try:
            logger.debug("Login new session, click button login to redirect to page login.")
            xpath_by_property = f"//button[@data-testid='menu-account-out-btn']"
            x_path_by_text = f"//button[text()='Login']"
            button_login = Button(self.driver, "XPATH", f"{xpath_by_property} | {x_path_by_text}")
            button_login.click()
            time.sleep(4)
            input_email = TextArea(self.driver, "XPATH", f"//input[@data-testid='menu-login-username']")
            input_email.write(username)
            input_password = TextArea(self.driver, "XPATH", f"//input[@data-testid='menu-login-password']")
            input_password.write(password)
            logger.info("Enter login submit!")
            button_submit = Button(self.driver, "XPATH", f"//button[@data-testid='menu-login-submit']")
            button_submit.click()
            self._try_waiting_cloudflare()
        except:
            logger.info("Login failed.")

    def _try_waiting_cloudflare(self):
        time.sleep(4)
        for j in range(15):
            try:
                logger.info("Checking Cloudflare........")
                progress = TextArea(self.driver, "XPATH",
                                f"//div[@class='main-content']//h1[contains(text(),'clearance.deepl.com')]",
                                # f"//body//div[@class='main-wrapper']//div[@class='main-content']//h1 | //*//h1[contains(text(),'clearance.deepl.com')]",
                                # f"//head//title[contains(text(),'Just a moment...'] | //body//div[@class='main-wrapper']//div[@class='main-content']//h1 | //*//h1[contains(text(),'clearance.deepl.com')]",
                                optional=True)
                if logger.isEnabledFor(logging.NOTSET):
                    self.driver.save_screenshot(f"./cloudflare/Waiting__clearance__progress_{j}.png")
                    with open(f"./cloudflare/Waiting__clearance__progress_{j}.html", "w", encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                if progress and progress.element:
                    time.sleep(7)
                    logger.info(f"*** waiting Cloudflare ::  {progress.element.text}")
                    progress = None
                else:
                    break
            except:
                pass

