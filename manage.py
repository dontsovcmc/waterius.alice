# coding: utf-8
from __future__ import unicode_literals

import json
import traceback
from flask import Flask, request, render_template
import random
import settings
from dialog import handle_dialog, pp
from mos_api import api
from emp_mos_api import AuthException
from storage import db
from logger import log


app = Flask(__name__)


@app.route("/alice-webhook", methods=['POST'])
def main():
    log.info('Request: %r', pp.pprint(request.json))

    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False
        }
    }

    try:
        handle_dialog(request.json, response)
    except Exception as err:
        log.error('{}'.format(traceback.format_exc()))
        response['response']['text'] = 'Что-то пошло не так'

        log.error('Response: %r', pp.pprint(response))

    return json.dumps(
        response,
        ensure_ascii=False,
        indent=2
    )


def handle_login_page(user_id, random_id):
    if request.method == 'GET':
        return render_template('mos_login_page.html', show_form=True)

    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            client = api.client(user_id)
            client.login(username, password)
            db.set(user_id, 'username', username)
            db.set(user_id, 'password', password)

            # client.logout(user_id)

            if random_id:
                return render_template('mos_login_page.html', show_form=False,
                                       message='Успех! Назовите Алисе код: {} в течении минуты'.format(user_id))
            else:
                return render_template('mos_login_page.html', show_form=False,
                                       message='Успех! Теперь вы можете попросить Алису отправить показания')

        except AuthException as err:
            log.error('{}'.format(traceback.format_exc()))
            return render_template('mos_login_page.html', show_form=True, username=username,
                                   message='Ошибка авторизации')
        except Exception as err:
            log.error('{}'.format(traceback.format_exc()))
            return render_template('mos_login_page.html', show_form=True, username=username,
                                   message='Ошибка сервера')


@app.route("/alice-webhook/mos_login_page/<user_id>", methods=['GET', 'POST'])
def mos_login_page(user_id):
    return handle_login_page(user_id, False)


@app.route("/alice-login", methods=['GET', 'POST'])
def alice_login():
    random_id = random.randint(100000, 999999)
    return handle_login_page(random_id, True)


if __name__ == '__main__':
    app.run(debug=settings.DEBUG, host=settings.HOST, port=settings.PORT)
