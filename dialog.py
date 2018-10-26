# coding: utf-8
from __future__ import unicode_literals

import logging
import pprint
from mos_api import mos_api
from emp_mos_api.mos import get_flat_id, \
    get_watercounter_last_value, get_watercounter_water_name, get_watercounters_by_type, \
    COLD_WATER, HOT_WATER, watercounter_new_value_json, get_watercounter_id
from emp_mos_api import AuthException
import settings

pp = pprint.PrettyPrinter(indent=4)
logging.basicConfig(level=logging.DEBUG)

# Хранилище данных о пользователях.
from storage import db


def has_hot(tokens):
    return [t for t in tokens if t in ['гвс',
                                       'горячей',
                                       'горячая',
                                       'горячую']]


def has_cold(tokens):
    return [t for t in tokens if t in ['хвс',
                                       'холодный',
                                       'холодная',
                                       'холодную']]


def handle_dialog(req, res):
    user_id = req['session']['user_id']
    res['response']['text'] = ''

    if req['session']['new']:
        if not db.get(user_id, ''):  # Это новый пользователь
            res['response']['text'] = 'Привет! Я могу отправить показания воды в Москве.'
    else:
        res['response']['text'] = ''

    original_utterance = req['request']['original_utterance']
    if original_utterance in ['удали']:
        [db.delete(user_id, f) for f in ['', 'username', 'password'] if db.get(user_id, f)]

        res['response']['text'] = 'Я удалила ваши данные'
        return

    if not db.get(user_id, 'username') or not db.get(user_id, 'password'):
        res['response']['text'] += 'Для отправки показаний мне не хватает логина. Введи его вручную.'
        res['response']['buttons'] = [{
                "title": "Авторизоваться",
                "url": settings.SITE + "/alice-webhook/mos_login_page/" + user_id,
                "hide": True
            }]
    else:
        if not mos_api.is_active(user_id):
            mos_api.login(db.get(user_id, 'username'), db.get(user_id, 'password'), user_id)

    handle_send(req, res)


def read_user_watercounters(user_id):
    """
    Считываем с сайта квартиру, счетчики пользователя и сохраняем в db
    :param user_id:
    :return:
    """
    f = db.get(user_id, 'flat')
    if not f:

        if not mos_api.is_active(user_id):
            mos_api.login(db.get(user_id, 'username'), db.get(user_id, 'password'), user_id)

        f = mos_api.get_flats(user_id)[0]
        db.set(user_id, 'flat', f)

    hw = db.get(user_id, 'hot')
    cw = db.get(user_id, 'cold')
    if not hw or not cw:

        if not mos_api.is_active(user_id):
            mos_api.login(db.get(user_id, 'username'), db.get(user_id, 'password'), user_id)

        wm = mos_api.get_watercounters(get_flat_id(f), user_id)
        hw = get_watercounters_by_type(HOT_WATER, wm)
        db.set(user_id, 'hot', hw)
        cw = get_watercounters_by_type(COLD_WATER, wm)
        db.set(user_id, 'cold', cw)


def handle_send(req, res):
    user_id = req['session']['user_id']

    tokens = req['request']['nlu']['tokens']

    for water, value_field in [('hot', 'new_hot'),
                               ('cold', 'new_cold')]:
        if db.get(user_id, value_field):
            if [t for t in tokens if t in ['да',
                                           'конечно',
                                           'естесственно']]:
                out = [watercounter_new_value_json(get_watercounter_id(db.get(user_id, water)),
                                                   db.get(user_id, value_field))]
                #mos_api.send_watercounters(get_flat_id(db.get(user_id, 'flat')), out)
                db.delete(user_id, value_field)
                res['response']['text'] = 'Отправлено. Жду новых команд.'
            elif [t for t in tokens if t in ['отмена',
                                             'нет',
                                             'стой',
                                             'стоп']]:
                db.delete(user_id, value_field)
                res['response']['text'] = 'Отменено.'
            else:
                res['response']['text'] = 'Я жду подтверджения отправки воды. Скажите да, нет, отмена.'

    if [t for t in tokens if t in ['текущие',
                                   'сейчас',
                                   'покажи',
                                   'назови',
                                   'произнеси',
                                   'поделись',
                                   'показывает']]:
        try:
            read_user_watercounters(user_id)

            hw = db.get(user_id, 'hot')
            cw = db.get(user_id, 'cold')

            if has_hot(tokens) and hw:
                res['response']['text'] += '{} {}\n'.format(get_watercounter_water_name(hw[0]),
                                                            get_watercounter_last_value(hw[0]))
            elif has_cold(tokens) and cw:
                res['response']['text'] += '{} {}\n'.format(get_watercounter_water_name(cw[0]),
                                                            get_watercounter_last_value(cw[0]))
            else:
                if hw:
                    res['response']['text'] += '{} {}\n'.format(get_watercounter_water_name(hw[0]),
                                                                get_watercounter_last_value(hw[0]))
                if cw:
                    res['response']['text'] += '{} {}\n'.format(get_watercounter_water_name(cw[0]),
                                                                get_watercounter_last_value(cw[0]))

            if not cw and not hw:
                res['response']['text'] = 'Добавь в приложение счетчики'

        except AuthException as err:
            logging.error(err)
            res['response']['text'] = 'Что-то не то с авторизацией. Повтори ее.'
            res['response']['buttons'] = [{
                    "title": "Авторизоваться",
                    "url": "https://waterius.ru/alice-webhook/mos_login_page/" + user_id,
                    "hide": True
                }]
        except Exception as err:
            logging.error(err)
            res['response']['text'] = 'Я не шмогла.'

    elif [t for t in tokens if t in ['передай',
                                     'отправь',
                                     'новые',
                                     'перешли',
                                     'отошли']]:
        res['response']['text'] += 'Назовите Горячая или Холодная вода плюс значение'

    else:
        entities = req['request']['nlu']['entities']
        evalue = filter(lambda x: x['type'] == 'YANDEX.NUMBER', entities)

        read_user_watercounters(user_id)

        if has_hot(tokens):
            if len(evalue) == 1:
                hw = db.get(user_id, 'hot')
                if hw:
                    db.set(user_id, 'new_hot', evalue[0]['value'])
                    res['response']['text'] += 'Горячая вода {}, отправляю?'.format(evalue[0]['value'])
                return

        elif has_cold(tokens):
            if len(evalue) == 1:
                cw = db.get(user_id, 'cold')
                if cw:
                    db.set(user_id, 'new_cold', evalue[0]['value'])
                    res['response']['text'] += 'Холодная вода {}, отправляю?'.format(evalue[0]['value'])
                return
        else:
            res['response']['text'] = 'Скажите Холодная Горячая вода и значение или спросите текущие показания'

