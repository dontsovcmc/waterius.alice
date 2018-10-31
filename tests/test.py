
import os
from unittest import TestCase

from dialog import handle_dialog
from storage import db
from mos_api import api


class FakeAlice(object):
    """
    Вопрос + ответ
    """
    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id', '1')
        self.request = self.init_request(**kwargs)
        self.response = self.init_response()

    def init_request(self, **kwargs):
        return {
            'version': '1.0',
            'session': {
                'user_id': kwargs.get('user_id', self.user_id),
                'new': kwargs.get('new', False)
            },
            'request': {
                'command': kwargs.get('command', ''),
                'nlu': {
                    'tokens': kwargs.get('tokens', kwargs.get('tokens', kwargs.get('command', '')
                                                                              .replace('.', ' ')
                                                                              .replace(',', ' ')
                                                                              .split(' '))),
                    'entities': kwargs.get('entities', kwargs.get('entities', ''))
                },
                'original_utterance': kwargs.get('original_utterance', kwargs.get('command', '')),
                'type': 'SimpleUtterance'
            }
        }

    def init_response(self):
        return {
            'version': self.request['version'],
            'session': self.request['session'],
            'response': {
                'end_session': False,
                'text': '',
                'buttons': []
            }
        }

    def say(self, **kwargs):
        self.request = self.init_request(**kwargs)
        self.response = self.init_response()
        return self.request


cold_watermeter = { u'checkup': u'2021-08-08+03:00',  # дата поверки
                    u'counterId': 111,  # id счетчика в emp.mos.ru
                    u'num': u'123456',  # серийный номер счетчика
                    u'type': 1,  # ХВС
                    u'indications': [
                        {
                            u'indication': u'200.8',
                            u'period': u'2018-07-31+03:00'
                        }]
                    }

hot_watermeter = {  u'checkup': u'2021-08-08+03:00',
                    u'counterId': 222,
                    u'num': u'123456',
                    u'type': 2,  # ГВС
                    u'indications': [
                        {
                            u'indication': u'100.4',
                            u'period': u'2018-07-31+03:00'
                        }]
                    }


class FakeMosApiClient(object):

    def __init__(self, **kwargs):
        self._is_active = False
        self._counters = kwargs.get('counters')

    def is_active(self):
        return self._is_active

    def get_flats(self):
        return [{'flat_id': '123'}]

    def login(self, username, password):
        self._is_active = True
        return True

    def get_watercounters(self, flat_id):
        return {'counters': self._counters}


global api


user_id = ''.join(['{:02x}'.format(x) for x in os.urandom(16)])
username = ''.join(['{:02x}'.format(x) for x in os.urandom(16)])
password = ''.join(['{:02x}'.format(x) for x in os.urandom(16)])

clients = {}


def client(user_id):
    return clients[user_id]


api.client = client

alice = FakeAlice(user_id=user_id)


class TestMosApi(TestCase):

    def test_auth(self):
        """
        Тестируем
        """
        clients[user_id] = FakeMosApiClient()

        handle_dialog(alice.say(new=True, command='Привет'), alice.response)
        self.assertEqual('Привет! Я могу отправить показания воды в Москве.Я должна знать твой логин и пароль. '
                         'Нажми на кнопку и авторизируйся.',
                         alice.response['response']['text'])

        handle_dialog(alice.say(command='Привет'), alice.response)

        self.assertEqual('Я должна знать твой логин и пароль. Нажми на кнопку и авторизируйся.',
                         alice.response['response']['text'])

        self.assertEqual('Авторизоваться',
                         alice.response['response']['buttons'][0]['title'])

        try:
            # типа авторизировались
            db.set_username(user_id, username)
            db.set_password(user_id, password)

            handle_dialog(alice.say(command='Ну как?'), alice.response)
            self.assertEqual('Назовите воду и значение или спросите текущие показания',
                             alice.response['response']['text'])
            self.assertFalse(alice.response['response']['buttons'])

        finally:
            db.clean(user_id)  # удалили данные авторизации

    def test_send_watervalues(self):
        """
        Тестируем отправку показаний
        """
        clients[user_id] = FakeMosApiClient(counters=[cold_watermeter, hot_watermeter])

        # типа авторизировались
        db.set_username(user_id, username)
        db.set_password(user_id, password)

        try:
            handle_dialog(alice.say(command='Привет'), alice.response)
            self.assertEqual('Назовите воду и значение или спросите текущие показания',
                             alice.response['response']['text'])
            self.assertFalse(alice.response['response']['buttons'])

            handle_dialog(alice.say(command='Алиса, скажи текущие показания'), alice.response)
            self.assertEqual('горячая вода 100.4\nхолодная вода 200.8\n', alice.response['response']['text'])

            entities = [dict(type='YANDEX.FIO', value=dict(first_name='алиса')),
                        dict(type='YANDEX.NUMBER', value=100.9)]
            handle_dialog(alice.say(command='Алиса, холодная вода 100.9', entities=entities), alice.response)
            self.assertEqual('Холодная вода 100.9, отправляю?', alice.response['response']['text'])

            handle_dialog(alice.say(command='тут написан бред для проверки не понимания'), alice.response)
            self.assertEqual('Я жду подтверджения отправки воды. Скажите да, нет, отмена.', alice.response['response']['text'])

            handle_dialog(alice.say(command='да'), alice.response)
            self.assertEqual('Отправлено. Жду новых команд.', alice.response['response']['text'])

            handle_dialog(alice.say(command='съешь еще этих французских булочек'), alice.response)
            self.assertEqual('Назовите воду и значение или спросите текущие показания', alice.response['response']['text'])

        finally:
            db.clean(user_id)  # удалили данные авторизации

    def test_one_counter(self):

        clients[user_id] = FakeMosApiClient(counters=[cold_watermeter])

        # типа авторизировались
        db.set_username(user_id, username)
        db.set_password(user_id, password)

        try:
            handle_dialog(alice.say(command='Привет'), alice.response)
            self.assertEqual('Назовите воду и значение или спросите текущие показания',
                             alice.response['response']['text'])
            self.assertFalse(alice.response['response']['buttons'])

            handle_dialog(alice.say(command='Алиса, скажи текущие показания'), alice.response)
            self.assertEqual('холодная вода 200.8\n', alice.response['response']['text'])

            entities = [dict(type='YANDEX.FIO', value=dict(first_name='алиса')),
                        dict(type='YANDEX.NUMBER', value=100.9)]
            handle_dialog(alice.say(command='Алиса, горячая вода 100.9', entities=entities), alice.response)
            self.assertEqual('Нет счетчика горячей воды в Госуслугах', alice.response['response']['text'])

        finally:
            db.clean(user_id)

    def test_no_counter(self):

        clients[user_id] = FakeMosApiClient()

        # типа авторизировались
        db.set_username(user_id, username)
        db.set_password(user_id, password)

        try:
            handle_dialog(alice.say(command='Привет'), alice.response)
            self.assertEqual('Назовите воду и значение или спросите текущие показания',
                             alice.response['response']['text'])
            self.assertFalse(alice.response['response']['buttons'])

            handle_dialog(alice.say(command='Алиса, скажи текущие показания'), alice.response)
            self.assertEqual('Добавь в приложение счетчики', alice.response['response']['text'])

            entities = [dict(type='YANDEX.FIO', value=dict(first_name='алиса')),
                        dict(type='YANDEX.NUMBER', value=100.9)]
            handle_dialog(alice.say(command='Алиса, горячая вода 100.9', entities=entities), alice.response)
            self.assertEqual('Нет счетчика горячей воды в Госуслугах', alice.response['response']['text'])

        finally:
            db.clean(user_id)