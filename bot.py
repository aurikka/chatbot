# -*- coding: utf-8 -*-
import datetime

import vk_api
from pony.orm import db_session, commit
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import logging
import _settings
import handlers
from models import Registration, UserState, Flight
import requests
import create_flight_table
import os.path

try:
    from _settings import tok, vk_group_id
except ImportError:
    tok = None
    vk_group_id = None
    print('Для работы бота необходим токен')
    exit()

log = logging.getLogger('bot')


class QuitError(Exception):

    def __init__(self):
        pass


def configure_logging():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    stream_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler('bot.log', encoding='utf8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    file_handler.setLevel(logging.DEBUG)

    log.addHandler(stream_handler)
    log.addHandler(file_handler)
    log.setLevel(logging.INFO)


# class UserState:
#     """ Состояние пользователя внутри сценария"""
#     def __init__(self, scenario_name, step_name, context=None):
#         self.scenario_name = scenario_name
#         self.step_name = step_name
#         self.context = context or {}


class Bot:
    """
    Echo bot для vk.com сообщества
    Use Python 3.8
    """

    def __init__(self, group_id, token):
        """
        :param group_id: group id из группы vk
        :param token: секретный уникальный токен группы
        """
        self.group_id = group_id
        self.token = token
        self.vk = vk_api.VkApi(token=self.token)
        self.long_poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()
        self.user_states = dict()   # user_id -> UserState
        self.json_schedule = {}

    def run(self):
        """
        запуск бота

        """
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception:
                log.exception('ошибка в обработке события')

    @db_session
    def on_event(self, event):
        """
        обрабатывает полученные текстовые сообщения
        :param event: событие VkBotMessageEvent object

        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            log.info('Мы пока не умеем обрабатывать событие такого типа %s', event.type)
            return
        user_id = event.object.peer_id
        text = event.object.text
        state = UserState.get(user_id=str(user_id))

        try:
            if state is not None:
                # юзер уже в базе и начал процесс бронирования (или регистрации)
                if r'/' in text:
                    self.do_command(text, state, user_id)
                else:
                    self.continue_scenario(text, state, user_id)
            else:
                # search intent
                if r'/' in text:
                    self.do_command(text, state, user_id)
                else:
                    count = 0
                    for intent in _settings.INTENTS:
                        if any(token in text.lower() for token in intent['tokens']):
                            if intent['answer']:
                                self.send_text(intent['answer'], user_id)
                            else:
                                self.start_scenario(intent['scenario'], user_id, text)
                            break
                        count += 1
                        if count == 5:
                            self.send_text(text_to_send=_settings.DEFAULT_ANSWER, user_id=user_id)
        except QuitError:
            pass

    def do_command(self, text, state, user_id):
        # если команда, выполняем
        if '/quit' in text:
            if state:
                self.send_text(text_to_send=_settings.COMMANDS['/quit']['answer'], user_id=user_id)
                state.delete()
                raise QuitError
        elif '/help' in text:
            self.send_text(text_to_send=_settings.COMMANDS['/help']['answer'], user_id=user_id)
            if state:
                self.continue_scenario(text, state, user_id)
        elif '/ticket' in text:
            if state:
                if state.scenario_name == 'registration':
                    state.delete()
                    self.start_scenario(_settings.SCENARIOS['flight'], user_id, text)
                elif state.scenario_name == 'flight':
                    self.send_text('Вы уже находитесь в сценарии бронирования билета', user_id)
                    self.continue_scenario(state.scenario_name, user_id, text)
            else:
                self.start_scenario('flight', user_id, text)
        else:
            self.send_text(text_to_send=_settings.WRONG_COMMAND, user_id=user_id)

    def continue_scenario(self, text, state, user_id):
        steps = _settings.SCENARIOS[state.scenario_name]['steps']
        step = steps[state.step_name]
        handler = getattr(handlers, step['handler'])
        if handler(text=text, context=state.context):
            # ведем пользователя на следующий шаг
            next_step = steps[step['next_step']]
            self.send_step(state, next_step, user_id, text)
            if next_step['next_step']:
                # проверяем, не последний ли это шаг
                state.step_name = step['next_step']
            else:
                # finish scenario
                if state.scenario_name == 'flight':
                    Flight(city_from=state.context['city_from'],
                           city_to=state.context['city_to'],
                           flight_date=state.context['date'],
                           flight_number=state.context['flight'],
                           seats=state.context['seats'],
                           comments=state.context['comments'],
                           phone=state.context['phone'])
                    state.delete()
                else:
                    log.info('Зарегистрирован: {name}{email}'.format(**state.context))
                    Registration(name=state.context['name'], email=state.context['email'])
                    state.delete()
        else:
            # хендлер вернул false, просим ввести данные повторно
            text_to_send = step['failure_text'].format(**state.context)
            self.send_text(text_to_send, user_id)

    def send_text(self, text_to_send, user_id):
        random_id = get_random_id()
        self.api.messages.send(message=text_to_send,
                               random_id=random_id,
                               peer_id=user_id)

    def send_image(self, image, user_id):
        upload_url_1 = self.api.photos.getMessagesUploadServer()
        upload_url = upload_url_1['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.png', image, 'image/png')}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)
        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'
        random_id = get_random_id()
        self.api.messages.send(message='',
                               attachment=attachment,
                               random_id=random_id,
                               peer_id=user_id)

    def send_schedule(self, json_file, user_id):
        for key in json_file:
            text_to_send = str(key) + '. ' + json_file[key]
            self.send_text(text_to_send, user_id)

    def check_up(self, state, text_to_send, user_id):
        self.send_text(text_to_send, user_id)
        try:
            if state.context['stop_scenario']:
                state.delete()
                commit()
        except KeyError:
            pass

    def send_step(self, state, step, user_id, text):
        if 'check_up' in step:
            checker = getattr(handlers, step['check_up'])
            text_to_send = checker(state.context)
            self.check_up(state, text_to_send, user_id)
        if 'text' in step:
            try:
                if not state.context['stop_scenario']:
                    self.send_text(text_to_send=step['text'].format(**state.context), user_id=user_id)
            except KeyError:
                self.send_text(text_to_send=step['text'].format(**state.context), user_id=user_id)
        if 'image' in step:
            handler = getattr(handlers, step['image'])
            image = handler(text, state.context)
            self.send_image(image, user_id)
        if 'json' in step:
            handler = getattr(handlers, step['json'])
            self.json_schedule = handler(text, state.context)
            state.context['schedule'] = self.json_schedule
            self.send_schedule(self.json_schedule, user_id)
        if 'approval' in step:
            text_to_send = 'Перелет {route}, рейс {flight}, количество мест {seats},' \
                           ' комментарии - {comments}'.format(**state.context)
            self.send_text(text_to_send, user_id)

    def start_scenario(self, scenario_name, user_id, text):
        scenario = _settings.SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        UserState(user_id=str(user_id), scenario_name=scenario_name, step_name=first_step, context={})
        state = UserState.get(user_id=str(user_id))
        self.send_step(state, step, user_id, text=text)


if __name__ == "__main__":
    today = datetime.date.today()
    configure_logging()
    if os.path.exists('flights_table.json'):
        os.remove('flights_table.json')
    create_flight_table.create_flight_table(day=today)
    chatbot = Bot(group_id=vk_group_id, token=tok)
    chatbot.run()
