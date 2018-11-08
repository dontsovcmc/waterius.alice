
import traceback
import pprint
import settings
from logger import log
from mos_api import api
from emp_mos_api import AuthException, Water, Watercounter

pp = pprint.PrettyPrinter(indent=4)


# Хранилище данных о пользователях.
from storage import db


def auth_button(user_id):
    return dict(title="Авторизоваться",
                url=settings.SITE + "/alice-webhook/mos_login_page/" + user_id,
                hide=True)


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
    tokens = req['request']['nlu']['tokens']
    res['response']['text'] = ''

    if req['session']['new']:
        res['response']['text'] = 'Привет! Я могу отправить показания воды в Москве.'

    if [t for t in tokens if t in ['удали']]:
        db.clean(user_id)
        res['response']['text'] = 'Я удалила ваши данные'
        return

    # Если пользователь не авторизирован в госуслугах,
    # проверим, что он произнес кодовое слово
    if not db.get_username(user_id) or not db.get_password(user_id):
        try:
            random_id = int(''.join(tokens))
            if 100000 <= random_id <= 999999:
                username = db.get_username(random_id)
                password = db.get_password(random_id)
                if username and password:
                    db.set_username(user_id, username)
                    db.set_password(user_id, password)
                    db.clean(random_id)

        except Exception as err:
            pass

    if not db.get_username(user_id) or not db.get_password(user_id):
        res['response']['text'] += 'Я не знаю твои логин и пароль. ' \
                                   'Нажми на кнопку или произнеси кодовое слово для авторизации.'
        res['response']['buttons'] = [auth_button(user_id)]
        return
    else:
        client = api.client(user_id)
        if not client.is_active():
            client.login(db.get_username(user_id), db.get_password(user_id))
            #log.info('login OK: ' + db.get_username(user_id))

    handle_send(req, res)


def read_user_watercounters(user_id):
    """
    Считываем с сайта квартиру, счетчики пользователя и сохраняем в db
    :param user_id:
    :return:
    """
    client = api.client(user_id)

    f = db.get_flat(user_id) or client.get_flats()[0]
    db.set_flat(user_id, f)

    wc = db.get(user_id, 'wc') or client.get_watercounters(f['flat_id'])['counters']

    if wc:
        cold = list(filter(lambda x: x['type'] == Water.COLD, wc))
        hot = list(filter(lambda x: x['type'] == Water.HOT, wc))
        db.set_cold(user_id, cold)
        db.set_hot(user_id, hot)
        return cold, hot
    else:
        return None, None


def handle_send(req, res):
    user_id = req['session']['user_id']
    client = api.client(user_id)
    tokens = req['request']['nlu']['tokens']

    if db.get_out(user_id):
        if [t for t in tokens if t in ['да',
                                       'конечно',
                                       'естесственно']]:
            #client.send_watercounters(db.get_flat(user_id)['flat_id'], db.get_out(user_id))
            db.delete_out(user_id)
            res['response']['text'] += 'Отправлено. Жду новых команд.'
            return

        elif [t for t in tokens if t in ['отмена',
                                         'нет',
                                         'стой',
                                         'стоп']]:
            db.delete_out(user_id)
            res['response']['text'] += 'Отменено.'

        else:
            res['response']['text'] += 'Я жду подтверджения отправки воды. Скажите да, нет, отмена.'
            return

    if [t for t in tokens if t in ['передай',
                                   'отправь',
                                   'новые',
                                   'перешли',
                                   'отошли']]:
        res['response']['text'] += 'Назовите Горячая или Холодная вода плюс значение'

    elif [t for t in tokens if t in ['текущие',
                                     'сейчас',
                                     'покажи',
                                     'назови',
                                     'произнеси',
                                     'поделись',
                                     'показывает']]:
        try:
            cold, hot = read_user_watercounters(user_id)

            if hot and has_hot(tokens):
                res['response']['text'] += '{} {}\n'.format(Water.name(hot[0]['type']),
                                                            Watercounter.last_value(hot[0]))
            elif cold and has_cold(tokens):
                res['response']['text'] += '{} {}\n'.format(Water.name(cold[0]['type']),
                                                            Watercounter.last_value(cold[0]))
            else:
                if hot:
                    res['response']['text'] += '{} {}\n'.format(Water.name(hot[0]['type']),
                                                                Watercounter.last_value(hot[0]))
                if cold:
                    res['response']['text'] += '{} {}\n'.format(Water.name(cold[0]['type']),
                                                                Watercounter.last_value(cold[0]))

            if not hot and not cold:
                res['response']['text'] += 'Добавь в приложение счетчики'

        except AuthException as err:
            log.error(err)
            res['response']['text'] += 'Что-то не то с авторизацией. Повтори ее.'
            res['response']['buttons'] = [auth_button(user_id)]
        except Exception as err:
            log.error('{}'.format(traceback.format_exc()))
            res['response']['text'] = 'Я не шмогла.'

    else:
        ya_num = list(filter(lambda x: x['type'] == 'YANDEX.NUMBER',
                                req['request']['nlu']['entities']))

        cold, hot = read_user_watercounters(user_id)

        if has_hot(tokens):
            if not hot:
                res['response']['text'] = 'Нет счетчика горячей воды в Госуслугах'
            elif len(ya_num) == 1:
                db.set_out(user_id, [hot[0]['num'], ya_num[0]['value']])
                res['response']['text'] += 'Горячая вода {}, отправляю?'.format(ya_num[0]['value'])
                return

        elif has_cold(tokens):
            if not cold:
                res['response']['text'] = 'Нет счетчика холодной воды в Госуслугах'
            elif len(ya_num) == 1:
                db.set_out(user_id, [cold[0]['num'], ya_num[0]['value']])
                res['response']['text'] += 'Холодная вода {}, отправляю?'.format(ya_num[0]['value'])
                return
        else:
            res['response']['text'] += 'Назовите воду и значение или спросите текущие показания'

    if not res['response']['text']:
        res['response']['text'] = 'Я тебя не понимаю'
