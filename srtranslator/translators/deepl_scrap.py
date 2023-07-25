import time
import logging
import timeit
import pickle

from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.proxy import Proxy

from .base import Translator, TimeOutException
from .selenium_utils import (
    create_proxy,
    create_driver,
    TextArea,
    Button,
    Text,
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

    def __init__(self, driver: Optional[WebDriver] = None):
        self.last_translation_failed = False # last_translation_failed is False still stop drive and retry proxy new, try proxy still failed is True
        self.driver = driver

        if self.driver is None:
            self._rotate_proxy()
            return

        self._reset()

    def _reset(self):
        logging.info(f"Going to {self.url}")
        self.driver.get(self.url)
        # cookie_headers = 'releaseGroups=2349.DWFA-553.2.2_1780.DM-872.2.2_1808.DF-3339.2.2_2346.DF-3049.1.2_1219.DAL-136.2.3_2067.SEO-205.2.3_2359.WDW-155.2.2_2350.TACO-8.2.2_2345.DM-1001.2.2_1776.B2B-345.2.2_2305.WDW-122.1.1_2381.TC-822.1.3_2370.DAL-568.2.1_1444.DWFA-362.2.2_2374.DWFA-542.1.2_2377.DUI-131.1.1_976.DM-667.2.3_2024.SEO-103.1.4_1583.DM-807.2.5_2382.WDW-165.1.1_2256.DF-3461.2.2_866.DM-592.2.2_2358.TACO-20.2.2_2274.DM-952.2.2_1577.DM-594.2.3_1119.B2B-251.2.4_2022.DF-3340.2.2_2347.DF-3557.2.2_2025.ACL-24.2.3_2356.B2B-515.2.2_1084.TG-1207.2.3_1997.DM-941.2.3_1327.DWFA-391.2.2_1483.DM-821.2.2_2380.DWFA-494.1.1_2068.DF-3045.2.3_2365.WDW-179.2.2_2055.DM-814.2.3_1585.DM-900.2.3_1332.DM-709.2.2_2351.TACO-21.2.2_2357.TACO-19.1.2_220.DF-1925.1.9_863.DM-601.2.2_1571.DM-791.2.4_2366.WDW-189.2.2_2307.WDW-25.2.2_975.DM-609.2.3_2383.DF-3505.1.1; dapUid=4f616eae-34b4-4a07-87c5-4bc37d397ad7; dapSid=%7B%22sid%22%3A%2265bde19c-a62a-4ee3-80e3-f555a9713113%22%2C%22lastUpdate%22%3A1690130685%7D; privacySettings=%7B%22v%22%3A%221%22%2C%22t%22%3A1690070400%2C%22m%22%3A%22LAX_AUTO%22%2C%22consent%22%3A%5B%22NECESSARY%22%2C%22PERFORMANCE%22%2C%22COMFORT%22%2C%22MARKETING%22%5D%7D; dapVn=1; LMTBID=v2|d1655f78-54f2-489a-84c9-c939a3f9870b|11a94be065183dd228a7b38695963c01; dl_session=fa.2f8cb717-a674-4e7b-a18c-96eedd32e2b6; userCountry=VN'
        #
        # for cookie in cookie_headers.split(";"):
        #     name, value = cookie.split('=', 1)
        #     self.driver.add_cookie({'name': name, 'value': value})

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

    def _is_translated(self, original: str, translation: str) -> bool:
        if (
            len(translation) != 0
            and "[...]" not in translation
            and len(original.splitlines()) == len(translation.splitlines())
            and original != translation
        ): return True
        else:
            logging.info(f"not _is_translated splitlines {len(original.splitlines()) == len(translation.splitlines())}   {len(original.splitlines())} {len(translation.splitlines())}")
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
            self.input_lang_from.write(value=(clean_text),is_clipboard= True)
            logging.debug(f"TIME SET source {timeit.default_timer() - start}")
        except Exception as e:
            logging.warning("Error catch exception element.........................................................", e)
            self.last_translation_failed = True # is stop translate file no retry
            self._rotate_proxy()
            return self.translate(text, source_language, destination_language)

        time.sleep(5)
        # Maximun number of iterations 60 seconds
        for _ in range(60):
            try:
                translation = self.input_destination_language.value
                logging.info(f"translation output ::{_}: {timeit.default_timer() - start}")

                if self._is_translated(clean_text, translation):
                    # Reset the proxy flag -- is success - last not failed
                    self.last_translation_failed = False
                    return translation.replace("~|@[.]@|~", "[...]")
                time.sleep(2)
            except Exception as e:
                logging.warning("Error catch exception................................................................", e)

        # Maybe proxy got banned, so we try with a new proxy, but just once.
        if not self.last_translation_failed: # failing, see_ing default is failing but first time not failed
            self.last_translation_failed = True
            self._rotate_proxy()
            return self.translate(text, source_language, destination_language)

        self.quit()
        raise TimeOutException("Translation timed out - Had try proxy but still failed.")

    def quit(self):
        self.driver.quit()
