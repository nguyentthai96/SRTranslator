import time
import logging
import timeit
import pickle

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from .base import Translator, TimeOutException
from .selenium_utils import (
    create_proxy,
    create_driver,
    TextArea,
    Button,
    Text, BaseElement,
)


class DeeplTranslator(Translator):
    url = "https://www.deepl.com/translator"
    max_char = 8000
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
        logging.info(f"Going to {self.url}")
        self.driver.get(self.url)
        #
        self._set_login(self.username, self.password)

        self._closePopUp()

        self.input_lang_from = TextArea(
            self.driver, "CLASS_NAME", "lmt__source_textarea"
        )
        self.input_destination_language = TextArea(
            self.driver, "CLASS_NAME", "lmt__target_textarea"
        )

        self.src_lang = None
        self.target_lang = None

    def _rotate_proxy(self):
        if self.driver is not None:
            logging.info(" ======= Translation failed. Probably got banned. ======= ")
            logging.info("Rotating proxy")
            self.quit()

        proxy = create_proxy()
        self.driver = create_driver(proxy)
        self._reset()

    def _closePopUp(self):
        Button(
            self.driver,
            "CSS_SELECTOR",
            "[aria-label=Close]",
            wait_time=5,
            optional=True,
        ).click()

    def _set_source_language(self, language: str) -> None:
        self._set_language(language, "lmt__language_select--source")
        self.src_lang = language

    def _set_destination_language(self, language: str) -> None:
        self._set_language(language, "lmt__language_select--target")
        self.target_lang = language

    def _set_language(self, language: str, dropdown_class: str) -> None:
        # Click the languages dropdown button
        Button(self.driver, "CLASS_NAME", dropdown_class).click()

        # Get the language button to click based on is dl-test property or the text in the button
        xpath_by_property = (
            f"//button[@data-testid='translator-lang-option-{language}']"
        )
        x_path_by_text = f"//button[text()='{self.languages[language]}']"
        xpath = f"{xpath_by_property} | {x_path_by_text}"

        # Click the wanted language button
        Button(self.driver, "XPATH", xpath).click()

    def _set_login(self, username: str, password: str) -> None:
        time.sleep(5)
        user_logged = WebDriverWait(self.driver, 8).until(
            EC.presence_of_element_located(
                (By.XPATH, f"//div[@class='dl_header_menu_v2__buttons__emailName_container']"))
        )
        if user_logged:
            self.username_current = user_logged.text
        else:
            self.username_current = None
        logging.info(f"Username current login :: {self.username_current}")
        if len(self.username_current) > 0 > self.username_current.find(username):
            logging.info(f"Username existed logout user current {self.username_current}")
            # data-testid="menu-account-logout" Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-logout']").click()
            self.driver.execute_script('$(`[data-testid="menu-account-logout"]`).click()')
            time.sleep(5)
            self._closePopUp()
        elif len(self.username_current) > 0 and self.username_current.find(username) >= 0:
            return

        button_login = Button(self.driver, "XPATH", f"//button[@data-testid='menu-account-out-btn']")
        button_login.click()

        input_email = TextArea(self.driver, "XPATH", f"//input[@data-testid='menu-login-username']")
        input_email.write(username)
        input_password = TextArea(self.driver, "XPATH", f"//input[@data-testid='menu-login-password']")
        input_password.write(password)

        button_submit = Button(self.driver, "XPATH", f"//button[@data-testid='menu-login-submit']")
        button_submit.click()
        time.sleep(5)
        #
        notification = BaseElement(self.driver, "XPATH", f"//div[@data-testid='error-notification']", optional=True)
        if notification.element:
            logging.error(f"Check login status :: {notification.element.text}")
            logging.error(f"==========================================================================================")
        else:
            time.sleep(3)
            user_logged = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//div[@class='dl_header_menu_v2__buttons__emailName_container']"))
            )
            if user_logged:
                self.username_current = user_logged.text
            else:
                self.username_current = None
            logging.info(f"Now login with username :: {self.username_current}")

    def _is_translated(self, original: str, translation: str) -> bool:
        if (
                len(translation) != 0
                and "[...]" not in translation
                and len(original.splitlines()) == len(translation.splitlines())
                and original != translation
        ):
            return True
        else:
            logging.info(
                f"not _is_translated splitlines {len(original.splitlines()) == len(translation.splitlines())}   {len(original.splitlines())} {len(translation.splitlines())}")
            return False

    def translate(self, text: str, source_language: str, destination_language: str):
        try:
            start = timeit.default_timer()
            if source_language != self.src_lang:
                self._set_source_language(source_language)
            if destination_language != self.target_lang:
                self._set_destination_language(destination_language)

            clean_text = text.replace("[...]", "~|@[.]@|~")
            logging.debug(f"TIME SET lang {timeit.default_timer() - start}")
            self.input_lang_from.write(value=(clean_text), is_clipboard=True)
            logging.debug(f"TIME SET source {timeit.default_timer() - start}")
        except Exception as e:
            logging.warning("Error catch exception element.........................................................", e)

        time.sleep(5)
        # Maximun number of iterations 60 seconds
        for _ in range(25):
            try:
                translation = self.input_destination_language.value
                logging.info(f"translation output ::{_}: {timeit.default_timer() - start}")

                if self._is_translated(clean_text, translation):
                    # Reset the proxy flag -- is success - last not failed
                    self.last_translation_failed = False
                    return translation.replace("~|@[.]@|~", "[...]")
                time.sleep(2)
            except Exception as e:
                logging.warning("Error catch exception.............................................................", e)

        # Maybe proxy got banned, so we try with a new proxy, but just once.
        if not self.last_translation_failed:  # failing, see_ing default is failing but first time not failed
            self.last_translation_failed = True
            self._rotate_proxy()
            return self.translate(text, source_language, destination_language)

        self.quit()
        raise TimeOutException("Translation timed out - Had try proxy but still failed.")

    def quit(self):
        self.driver.quit()

    def retry(self):
        self._rotate_proxy()
