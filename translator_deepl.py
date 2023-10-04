import gzip
import json
import sys
import os
import glob
import time
import timeit
import shutil
from datetime import datetime
from typing import List

from srtranslator import SrtFile
from srtranslator.translators.deepl_handler import DeeplTranslator
from srtranslator.translators.selenium_utils import create_proxy, create_driver
import pathlib

import logging
import logging.handlers as handlers


class GZipRotator:
    def __call__(self, source, dest):
        os.rename(source, dest)
        f_in = open(dest, 'rb')
        f_out = gzip.open("%s.gz" % dest, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove(dest)

import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "-v",
    "--verbose",
    action="store_const",
    dest="loglevel",
    const=logging.INFO,
    default=logging.INFO,
    help="Increase output verbosity",
)

parser.add_argument(
    "-vv",
    "--debug",
    action="store_const",
    dest="loglevel",
    const=logging.DEBUG,
    default=logging.WARNING,
    help="Increase output verbosity for debugging",
)

parser.add_argument(
    '--conf',
    type=str,
    default="config.json",
    action='append',
    required=False,
    help="Config path file name format json. Default: config.json"
)

parser.add_argument(
    "-w",
    "--wrap-limit",
    type=int,
    default=1500,
    required=False,
    help="Number of characters -including spaces- to wrap a line of text. Default: 50",
)

parser.add_argument(
    "-i",
    "--src-lang",
    type=str,
    default="auto",
    help="Source language. Default: auto",
)

parser.add_argument(
    "-o",
    "--dest-lang",
    type=str,
    default="en-US",
    help="Destination language. Default: en-US (English)",
)

parser.add_argument(
    "-p",
    "--source-filepath",
    metavar="path",
    type=str,
    default='source_srt',
    help="File to translate",
)


parser.add_argument(
    "-usr",
    "--username",
    type=str,
    default="viphn8688@gmail.com",
    help="Username login account.",
)
parser.add_argument(
    "-usrpw",
    "--userpassword",
    type=str,
    default="*Um5h^a6X8VbTn7^",
    help="Password of account login.",
)
parser.add_argument(
    "-proxys",
    "--proxy-address",
    type=List[str],
    help="List proxy address [ip:port].",
)

parser.add_argument(
    "--proxy_required",
    type=bool,
    default=False,
    help="Require using first time.",
)

parser.add_argument(
    "--proxy_disable",
    type=bool,
    default=True,
    help="Disable proxy all.",
)

parser.add_argument(
    "-hidden",
    "--hidden-browser",
    action="store_false",
    help="Hidden background browser window",
)

parser.add_argument(
    "-browser",
    "--type-browser",
    type=str,
    default="firefox",
    help="Browser type firefox or chrome, default firefox.",
)


parser.add_argument(
    "--login_manual",
    type=bool,
    default=True,
    help="False is auto login.",
)

args=parser.parse_args()
if args.conf is not None and os.path.isfile(args.conf):
    with open(args.conf, 'r', encoding='utf-8') as f:
        parser.set_defaults(**json.load(f))

# Reload arguments to override config file values with command line values
args = parser.parse_args()
# /////////////////////////////////////////////////////////////////////////////////////////////////




stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(args.loglevel)  # logging.WARNING
# stdout_handler.setFormatter(formatter)

if not os.path.exists(pathlib.Path('logs').resolve()):
    os.makedirs(pathlib.Path('logs').resolve())
logHandler = handlers.RotatingFileHandler('logs/application_srt.log', maxBytes=102400, backupCount=100)
logHandler.rotator = GZipRotator()

logging.basicConfig(format='%(asctime)s,%(msecs)d  %(levelname)s   %(filename)s    %(message)s',
                    datefmt='%H:%M:%S',
                    level=args.loglevel,
                    handlers=[stdout_handler, logHandler]
                    )
logging.getLogger('selenium.webdriver.remote').setLevel(logging.INFO)
logging.getLogger('selenium.webdriver.common').setLevel(logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Application Starting Version :: 20231004 - product new version ui deepl")


#
try:
    os.environ.pop("MOZ_HEADLESS") # DISABLE_PROXY BROWSERS_TYPE LOGIN_AUTO


    if args.proxy_disable:
        os.environ["DISABLE_PROXY"] = "1"
    if args.hidden_browser:
        os.environ["MOZ_HEADLESS"] = "1" # MOZ_HEADLESS hidden browser using -headless

    os.environ["BROWSERS_TYPE"] = args.type_browser
    if not args.login_manual:
        os.environ["LOGIN_AUTO"] = "1"
except  Exception as error:
    logger.info("Exception parse :: {}", error)

# else:
#     os.environ["MOZ_HEADLESS"] = "0"


folder = pathlib.Path(args.source_filepath).resolve()
list_file = glob.glob(os.path.join(folder, "**/*.srt"), recursive=True)
if not os.path.exists(folder):
    os.makedirs(folder)
    logger.info(f"Please recheck copy file translate to folder path :: {folder}")
    sys.exit(-1)
else:
    logger.info(f"Processing translate Folder path :: {folder} size {len(list_file)} file.")

if len(list_file) < 1:
    logger.info(f"Please recheck copy file translate to folder path :: {folder}. No-any file translate.")
    sys.exit(-1)



proxy = None
if args.proxy_required:
    proxy = create_proxy(country_id=["US", "GB"], proxyAddresses=args.proxy_address)
driver = create_driver(proxy)
#
try:
    translator = DeeplTranslator(driver, username=args.username, password=args.userpassword)
    translator.max_char = args.wrap_limit
    translator.proxy_address = args.proxy_address
except Exception as e:
    logger.exception("Error init driver selenium :: ", e)
    logger.info("Waiting system stop.")
    if driver is not None:
        driver.quit()
    time.sleep(3)
    sys.exit(-1)


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
        logger.info(
            f"......... Files Translating {int(100 * progress / len(list_file))}%   files {tail}... (summary: {failed} failed)")
        srt = SrtFile(filepath)
        srt.translate(translator, args.src_lang, args.dest_lang)
        # srt.wrap_lines()
        srt.join_lines()

        filename, file_extension = os.path.splitext(tail)
        srt.save(os.path.join(pathtranslated, f"{filename}_{args.dest_lang}{file_extension}"))
        print(f"{tail}  with time {timeit.default_timer() - start}")
        shutil.move(filepath, os.path.join(source_completed, f"{tail}"))
        progress += 1
    except Exception as e:
        failed += 1
        logger.error(f"File {filepath} failed cannot save file translate (summary: {failed} failed).")
        logger.exception(f"Error process file :: {filepath}  Ex:", e)
        try:
            if translator is not None:
                translator.quit()
            proxy = None
            if not args.proxy_required:
                proxy = create_proxy(country_id=["US", "GB"])
            driver = create_driver(proxy)
            translator = DeeplTranslator(driver, username=args.username, password=args.userpassword)
            translator.max_char = args.wrap_limit
            translator.proxy_address = args.proxy_address
            if not args.proxy_required:
                translator.proxy_address = None
        except Exception as e:
            logger.exception(f"Retry init for next file (summary: {failed} failed). Exception start driver", e)
            driver = create_driver()
            translator = DeeplTranslator(driver, username=args.username, password=args.userpassword)

logger.info(
    f"====================================================================================================================================")
logger.info(
    f"_________________  Files Translating complete {int(100 * progress / len(list_file))}%   files  numbers {progress}/{len(list_file)}   ({failed} failed)  _________________")

translator.quit()
time.sleep(5)
