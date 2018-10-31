# coding: utf-8
from __future__ import unicode_literals
import json
import os

# загрузим переменные настроек из json файла, чтобы не хранить в git
globals().update(json.loads(open(os.path.join(os.path.dirname(__file__), os.pardir, 'alice.json')).read()))

DEBUG = locals().get('DEBUG', 'False').lower() == 'true'


""" Пример файла конфигурации alice.json
{
    "HOST": "x",
    "PORT": 1,
    "SITE": "http://127.0.0.1:10000",  для POST запроса кнопки
    "_SITE": "https://somename.ru",  
    "DEBUG": "True",
    "LOG_DIR": "E:\\1"
    
    для emp_mos_api
    "EMP_MOS_RU_TOKEN": "x",
    "EMP_MOS_RU_USER_AGENT": "x",
    "EMP_MOS_RU_GUID": "x",
    "EMP_MOS_RU_DEV_USER_AGENT": "Android",
    "EMP_MOS_RU_APP_VER": "x",
}
"""
