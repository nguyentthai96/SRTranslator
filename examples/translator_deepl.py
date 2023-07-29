import gzip
import sys
import os
import glob
import timeit
import shutil
from datetime import datetime

from srtranslator import SrtFile
from srtranslator.translators.deepl_handler import DeeplTranslator
from srtranslator.translators.selenium_utils import create_proxy, create_driver
import pathlib

import logging
import logging.handlers as handlers

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)  # logging.WARNING
# stdout_handler.setFormatter(formatter)

class GZipRotator:
    def __call__(self, source, dest):
        os.rename(source, dest)
        f_in = open(dest, 'rb')
        f_out = gzip.open("%s.gz" % dest, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove(dest)
if not os.path.exists(pathlib.Path('logs').resolve()):
    os.makedirs(pathlib.Path('logs').resolve())
logHandler = handlers.RotatingFileHandler('logs/application_srt.log', maxBytes=102400, backupCount=100)
logHandler.rotator = GZipRotator()

logging.basicConfig(format='%(asctime)s,%(msecs)d  %(levelname)s   %(filename)s    %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO,
                    handlers=[stdout_handler, logHandler]
                    )

logger = logging.getLogger(__name__)

folder = pathlib.Path('source_srt').resolve()
list_file = glob.glob(os.path.join(folder, "**/*.srt"), recursive=True)
if not os.path.exists(folder):
    os.makedirs(folder)
    logger.info(f"Please recheck copy file translate to folder path :: {folder}")
    sys.exit(-1)
else:
    logger.info(f"Processing translate Folder path :: {folder} size {len(list_file)} file.")

if len(list_file) <1:
    logger.info(f"Please recheck copy file translate to folder path :: {folder}. No-any file translate.")
    sys.exit(-1)

firefox_profile = pathlib.Path('tmp/firefox_profile').resolve()
if not os.path.exists(firefox_profile):
    os.makedirs(firefox_profile)

# proxy = create_proxy(country_id=["US", "GB"])
driver = create_driver()
# The country ids are the ones in https://www.sslproxies.org/
# translator = DeeplTranslator(driver, username='nguyentthai96@gmail.com', password='TThais12589')
translator = DeeplTranslator(driver, username='viphn8688@gmail.com', password='*Um5h^a6X8VbTn7^')

target_datetime = datetime.strptime('2023-08-20 01:50:00', '%Y-%m-%d %H:%M:%S')
current_datetime = datetime.now()
if current_datetime > target_datetime:
    print("Error - The current date and time are after the target date.")
    sys.exit(-1111)
start = timeit.default_timer()
pathtranslated = pathlib.Path('translated').resolve()
source_completed = pathlib.Path('source_completed').resolve()

if not os.path.exists(pathtranslated):
    os.makedirs(pathtranslated)
if not os.path.exists(source_completed):
    os.makedirs(source_completed)

progress = 0
failed = 0
for filepath in list_file:
    try:
        head, tail = os.path.split(filepath)
        logger.info(f"......... Files Translating {int(100 * progress / len(list_file))}%   files {tail}... ({failed} failed)")
        srt = SrtFile(filepath)
        srt.translate(translator, "auto", "en-US")
        # srt.wrap_lines()
        srt.join_lines()
        srt.save(os.path.join(pathtranslated, f"{tail}"))
        print(f"{tail}  with time {timeit.default_timer() - start}")
        shutil.move(filepath, os.path.join(source_completed, f"{tail}"))
        progress += 1
    except Exception as e:
        failed += 1
        logger.error(f"File {filepath} failed cannot save file translate ({failed} failed).")
        logger.error(f"Error process file :: {filepath}  Ex:",e)
        translator.quit()
        driver = create_driver()
        translator = DeeplTranslator(driver, username='viphn8688@gmail.com', password='*Um5h^a6X8VbTn7^')

logger.info(f"====================================================================================================================================")
logger.info(f"_________________  Files Translating complete {int(100 * progress / len(list_file))}%   files  numbers {progress}/{len(list_file)}   ({failed} failed)  _________________")

translator.quit()

