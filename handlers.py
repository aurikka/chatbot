"""
Handler - это функция, которая принимает на вход text (текст входящего сообщения) и context(dict), а возвращает bool:
True - если шаг пройден, False - если данные введены неправильно
"""
import re
import generate_ticket
import detect_near_city
import datetime
import json
import _settings


re_name = re.compile(r'^[\w\-\s]{3,40}$')
re_email = re.compile(r'\b[a-zA-z0-9_.+-]+@[a-zA-z0-9-]+\.[a-zA-z0-9-.]+\b')
re_city = re.compile(r'^[\w\-\s]{3,15}$')
re_phone = re.compile(r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{10}$')
re_date = re.compile(r'(0[1-9]|[12][0-9]|3[01])[- /.](0[1-9]|1[012])[- /.](20)\d\d')


def handler_name(text, context):
    match = re.match(re_name, text)
    if match:
        context['name'] = text
        return True
    else:
        return False


def handler_email(text, context):
    matches = re.findall(re_email, text)
    if len(matches) > 0:
        context['email'] = matches[0]
        return True
    else:
        return False


def generate_ticket_handler(text, context):
    return generate_ticket.generate_ticket(name=context['name'], email=context['email'])


def handler_ticket_avia(text, context):
    return generate_ticket.generate_avia_ticket(from_=context['city_from'], to_=context['city_to'],
                                                date=context['flight'])


def handler_city_from(text, context):
    match = re.match(re_city, text)
    if match:
        nearest_airport = detect_near_city.find_airport(text)
        if nearest_airport is None:
            return False
        else:
            context['city_from'] = nearest_airport
            return True
    else:
        return False


def handler_city_to(text, context):
    match = re.match(re_city, text)
    if match:
        nearest_airport = detect_near_city.find_airport(text)
        if nearest_airport is None:
            return False
        else:
            context['city_to'] = nearest_airport
            return True
    else:
        return False


def handler_date(text, context):
    match = re.match(re_date, text)
    if match:
        today = datetime.datetime.today()
        today = today - datetime.timedelta(days=1)
        last_day = today + datetime.timedelta(days=30)
        text_as_date = datetime.datetime.strptime(text, '%d-%m-%Y')
        if today < text_as_date < last_day:
            context['date'] = text
            return True
        else:
            return False
    else:
        return False


def routes_handler(text, context):
    routes_list = {}
    date_start = datetime.datetime.strptime(context['date'], '%d-%m-%Y')
    with open('flights_table.json', mode='r', encoding='UTF8') as fp:
        loaded_json_file = json.load(fp)
        route_schedule = loaded_json_file[context['route']]
        number = 1
        for key in route_schedule:
            key_date = datetime.datetime.strptime(key, '%Y-%m-%d')
            if date_start <= key_date:
                for time in route_schedule[key]:
                    routes_list[number] = key + ' в ' + time
                    number += 1
                    if number == 6:
                        return routes_list


def handler_user_choose(text, context):
    for key in context['schedule']:
        if str(key) == text:
            context['flight'] = context['schedule'][key]
            return True
    return False


def handler_seats(text, context):
    if int(text) < 6:
        context['seats'] = text
        return True
    else:
        return False


def handler_comments(text, context):
    if text:
        context['comments'] = text
    return True


def handler_approval(text, context):
    if text == 'да':
        context['approval'] = True
        return True
    if text == 'нет':
        context['approval'] = False
        return True
    else:
        return False


def handler_phone(text, context):
    match = re.match(re_phone, text)
    if match:
        context['phone'] = text
        return True
    else:
        return False


def check_city_from(context):
    text_to_send = _settings.WRONG_CITY_FROM.format(**context)
    return text_to_send


def check_city_to(context):
    route = context['city_from'] + ' - ' + context['city_to']
    context['route'] = route
    text_to_send = f'Выбранный маршрут: {route}'
    if route not in _settings.ROUTES:
        text_to_send = f'Выбранный маршрут: {route}' + 'Данный маршрут не существует. ' \
                                                       '\nПроцесс бронирования остановлен.' \
                                                       '\nЧтобы начать бронирование с начала, введите команду /ticket'
        context['stop_scenario'] = True
    return text_to_send


def check_approval(context):
    if not context['approval']:
        text_to_send = 'Ваше бронирование остановлено. ' \
                       'Вы можете начать бронирование с начала с помощью команды /ticket'
        context['stop_scenario'] = True
        return text_to_send
    else:
        context['stop_scenario'] = False
        text_to_send = 'Спасибо за подтверждение бронирования'
        return text_to_send
