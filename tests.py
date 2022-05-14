import os
from unittest import TestCase
from unittest.mock import patch, Mock
import datetime
import create_flight_table
from bot import Bot
from vk_api.bot_longpoll import VkBotMessageEvent
from copy import deepcopy
import _settings
from pony.orm import db_session, rollback
import generate_ticket
import filecmp


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()

    return wrapper


class Test1(TestCase):
    RAW_EVENT = {'type': 'message_new',
                 'object': {'date': 1596311711, 'from_id': 273019755, 'id': 55, 'out': 0, 'peer_id': 273019755,
                            'text': 'привет бот!', 'conversation_message_id': 54, 'fwd_messages': [],
                            'important': False, 'random_id': 0, 'attachments': [], 'is_hidden': False},
                 'group_id': 196734760, 'event_id': '60f984f7c1d103e1a6f1a18dbeee98df14f55585'}

    INPUTS = [
        'Привет',
        '/help',
        'забронировать билет',
        'москва',
        'екатеринбург',
        '27-12-2020',
        '3',
        '2',
        'комментарий',
        'да',
        '89030000000'
    ]

    EXPECTED_OUTPUTS = [
        _settings.INTENTS[4]['answer'],
        _settings.COMMANDS['/help']['answer'],
        _settings.SCENARIOS['flight']['steps']['step1']['text'],
        'Вам будут предложены рейсы из ближайшего аэропорта - Москва',
        _settings.SCENARIOS['flight']['steps']['step2']['text'],
        'Выбранный маршрут: Москва - Екатеринбург',
        _settings.SCENARIOS['flight']['steps']['step3']['text'],
        _settings.SCENARIOS['flight']['steps']['step4']['text'],
        '1. 2020-12-27 в 12-10',
        '2. 2020-12-28 в 11-15',
        '3. 2020-12-28 в 17-25',
        '4. 2020-12-28 в 21-30',
        '5. 2020-12-30 в 11-15',
        _settings.SCENARIOS['flight']['steps']['step5']['text'],
        _settings.SCENARIOS['flight']['steps']['step6']['text'],
        _settings.SCENARIOS['flight']['steps']['step7']['text'],
        'Перелет Москва - Екатеринбург, рейс 2020-12-28 в 17-25, количество мест 2, комментарии - комментарий',
        'Спасибо за подтверждение бронирования',
        _settings.SCENARIOS['flight']['steps']['step8']['text'],
        _settings.SCENARIOS['flight']['steps']['step9']['text'],
    ]

    def test_run(self):
        count = 5
        events = [{}] * count  # [{}, {}, ...]
        long_poller_mock = Mock(return_value=events)
        long_poller_listen_mock = Mock()
        long_poller_listen_mock.listen = long_poller_mock

        with patch('bot.vk_api.VkApi'), \
             patch('bot.VkBotLongPoll', return_value=long_poller_listen_mock):
            bot = Bot('', '')
            bot.on_event = Mock()
            bot.run()

            bot.on_event.assert_called()
            bot.on_event.assert_any_call({})

            assert bot.on_event.call_count == count

    @isolate_db
    def test_run_ok(self):

        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['text'] = input_text
            events.append(VkBotMessageEvent(event))

        if os.path.exists('flights_table.json'):
            os.remove('flights_table.json')
        date_start = datetime.datetime.strptime('27-12-2020', '%d-%m-%Y')
        create_flight_table.create_flight_table(date_start)

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)
        flight_dict = {1: '2020-12-27 в 12-10',
                       2: '2020-12-28 в 11-15',
                       3: '2020-12-28 в 17-25',
                       4: '2020-12-28 в 21-30',
                       5: '2020-12-30 в 11-15'}
        # Добавил новый патч - он заменяет дату today на указанную дату
        with patch('bot.VkBotLongPoll', return_value=long_poller_mock), \
             patch('handlers.datetime.date', Mock(today=Mock(return_value=datetime.date(2020, 12, 5)))):
            bot = Bot('', '')
            bot.api = api_mock
            bot.send_image = Mock()
            bot.json_schedule = flight_dict
            bot.run()

        assert send_mock.call_count == len(self.EXPECTED_OUTPUTS)

        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])
        for real, expec in zip(real_outputs, self.EXPECTED_OUTPUTS):
            print(real)
            print('-' * 50)
            print(expec)
            print('-' * 50)
            print(real == expec)
            print('_' * 50)
        # тест не срабатывает, отлетает на первом сообщении. исправлено
        assert real_outputs == self.EXPECTED_OUTPUTS

    def test_ticket_ok(self):
        created_ticket = generate_ticket.generate_avia_ticket('Москва', 'Екатеринбург', '2020-12-28 в 17-25')
        with open("created_test_ticket.png", "wb") as f:
            f.write(created_ticket.getbuffer())
        result = filecmp.cmp('created_test_ticket.png', 'reference_ticket.png', shallow=False)
        assert result is True

