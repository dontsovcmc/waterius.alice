# coding: utf-8
from __future__ import unicode_literals
import json
import os

DEBUG = False
# загрузим переменные настроек из json файла, чтобы не хранить в git
globals().update(json.loads(open(os.path.join(os.path.dirname(__file__), os.pardir, 'alice.json')).read()))

DEBUG = locals().get('DEBUG', 'False').lower() == 'true'