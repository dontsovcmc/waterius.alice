# -*- coding: utf-8 -*-
__author__ = 'dontsov'
import shelve


class Shelve(object):

    def __init__(self, title='shelve.db'):
        self.storage = None
        self.title = title

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        if not self.storage:
            self.storage = shelve.open(self.title)

    def close(self):
        if self.storage:
            self.storage.close()
        self.storage = None

    def delete(self, chat_id, field):
        try:
            del self.storage[str(chat_id) + str(field)]
            self.storage.sync()
        except Exception as err:
            pass

    def set(self, chat_id, field, value):
        self.storage[str(chat_id) + str(field)] = value
        self.storage.sync()  # !!!!

    def get(self, chat_id, field, default=None):
        try:
            return self.storage[str(chat_id) + str(field)]
        except KeyError:
            return default


class AliceDB(Shelve):

    def __init__(self, title='shelve.db'):
        Shelve.__init__(self, title)

    def clean(self, user_id):
        db.delete(user_id, 'username')
        db.delete(user_id, 'password')
        db.delete_out(user_id)

    def get_username(self, user_id):
        return db.get(user_id, 'username')

    def get_password(self, user_id):
        return db.get(user_id, 'password')

    def get_flat(self, user_id):
        return db.get(user_id, 'flat')

    def get_water(self, user_id):
        return db.get(user_id, 'wc')

    def set_username(self, user_id, username):
        db.set(user_id, 'username', username)

    def set_password(self, user_id, password):
        db.set(user_id, 'password', password)

    def set_flat(self, user_id, flat):
        db.set(user_id, 'flat', flat)

    def set_water(self, user_id, wc):
        db.set(user_id, 'wc', wc)

    def set_hot(self, user_id, value):
        db.set(user_id, 'hot', value)

    def set_cold(self, user_id, value):
        db.set(user_id, 'cold', value)

    def get_hot(self, user_id):
        db.get(user_id, 'hot')

    def get_cold(self, user_id):
        db.get(user_id, 'cold')

    def set_out(self, user_id, out):
        db.set(user_id, 'out', out)

    def get_out(self, user_id):
        return db.get(user_id, 'out')

    def delete_out(self, user_id):
        db.delete(user_id, 'out')


db = AliceDB()
db.open()
