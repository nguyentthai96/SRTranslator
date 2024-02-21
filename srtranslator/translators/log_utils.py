import gzip
import logging
import logging.handlers as handlers
import os
import pathlib
import sys


class GZipRotator:
    def __call__(self, source, dest):
        os.rename(source, dest)
        f_in = open(dest, 'rb')
        f_out = gzip.open("%s.gz" % dest, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove(dest)


# /////////////////////////////////////////////////////////////////////////////////////////////////

def log_config(args):
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(args.loglevel)  # logging.WARNING
    # stdout_handler.setFormatter(formatter)

    if not os.path.exists(pathlib.Path('logs').resolve()):
        os.makedirs(pathlib.Path('logs').resolve())
    log_handler = handlers.RotatingFileHandler('logs/application_srt.log', encoding="utf-8",
                                               maxBytes=102400, backupCount=100)
    log_handler.rotator = GZipRotator()

    # https://stackoverflow.com/questions/533048/how-to-log-source-file-name-and-line-number-in-python
    # logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)s %(filename)s:%(lineno)d[%(funcName)s] - %(message)s   %(pathname)s',
    logging.basicConfig(
        format='%(asctime)s,%(msecs)d %(levelname)s %(filename)s:%(lineno)d[%(funcName)s] - %(message)s',
        datefmt='%H:%M:%S',
        level=args.loglevel,
        handlers=[stdout_handler, log_handler]
        )
    logging.getLogger('selenium.webdriver.remote').setLevel(logging.INFO)
    logging.getLogger('selenium.webdriver.common').setLevel(logging.INFO)
