# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import sys
import settings
from datetime import datetime


class Logger(object):
    def __init__(self):
        log = logging.getLogger('')
        log.setLevel(logging.INFO)

        filename = datetime.utcnow().strftime('%Y.%m.%d_%H.%M_UTC.log')

        log_dir = getattr(settings, 'LOG_DIR', 'logs')
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        fh = logging.FileHandler(os.path.join(log_dir, filename), mode='w')
        fh.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        log.addHandler(fh)

        # Задействовать консоль для вывода лога
        console = sys.stderr
        if console is not None:
            # Вывод лога производится и на консоль и в файл (одновременно)
            console = logging.StreamHandler(console)
            console.setLevel(logging.INFO)
            console.setFormatter(formatter)
            log.addHandler(console)

Logger()

log = logging.getLogger('')
