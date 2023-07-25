import logging
import logging.handlers as handlers
import sys
import os
import glob
import timeit

from srtranslator import SrtFile
from srtranslator.translators.deepl_scrap import DeeplTranslator
from srtranslator.translators.selenium_utils import create_proxy, create_driver
import pathlib

stdout_handler = logging.StreamHandler(sys.stdout)
# stdout_handler.setLevel(logging.WARNING)
stdout_handler.setLevel(logging.DEBUG)
# stdout_handler.setFormatter(formatter)

logHandler = handlers.RotatingFileHandler('application_srt.log', maxBytes=51200, backupCount=2)
file_handler = logging.FileHandler('application_srt.log')
file_handler.setLevel(logging.DEBUG)
# file_handler.setFormatter(formatter) # filemode='a',

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)s %(name)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO,
                    handlers=[file_handler,stdout_handler, logHandler]
                    )


folder = pathlib.Path().resolve()
folderFiles = glob.glob(os.path.join(folder, "**/*.srt"), recursive=True)
logging.info(f"Processing translate Folder path :: {folder} size {len(folderFiles)} file.")
start = timeit.default_timer()

pathtranslated = pathlib.Path('translated').resolve()

if not os.path.exists(pathtranslated):
    os.makedirs(pathtranslated)

for filepath in folderFiles:
    try:
        head, tail = os.path.split(filepath)

        #proxy = create_proxy(country_id=["US", "GB"])
        driver = create_driver()
        # The country ids are the ones in https://www.sslproxies.org/
        translator = DeeplTranslator(driver)

        # logging.info(f"processing translate {filepath}")
        srt = SrtFile(filepath)
        srt.translate(translator, "zh", "en-US")
        # srt.wrap_lines()
        srt.join_lines()
        srt.save(os.path.join(pathtranslated, f"{tail}"))
        logging.info(f"{tail}  with time {timeit.default_timer() - start}")
        translator.quit()
    except:
        logging.error(f"File {filepath} failed cannot save file translate.")