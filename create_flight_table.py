import datetime
import _settings
import json
import os.path


def create_flight_table(day):
    if os.path.exists('flights_table.json'):
        os.remove('flights_table.json')
    result = {}
    # today = datetime.date.today()
    # print(only_day, day_of_week)
    all_flights = _settings.FLIGHTS_BASE
    for direction in all_flights:    # создаем словарь с раписанием вылетов по каждому направлению
        result[direction] = {}
        next_day = day    # было today
        for i in range(1, 32):
            next_day_str = datetime.date.strftime(next_day, "%Y-%m-%d")
            only_day = next_day_str.split('-')[2]
            result[direction][next_day_str] = []
            next_day_in_week = datetime.date.isoweekday(next_day)
            if next_day_in_week in all_flights[direction]['days']:
                for time in all_flights[direction]['time_for_day']:
                    result[direction][next_day_str].append(time)
            if only_day in all_flights[direction]['dates']:
                for time in all_flights[direction]['time_for_dates']:
                    result[direction][next_day_str].append(time)
            if not result[direction][next_day_str]:
                result[direction].pop(next_day_str)
            next_day = next_day + datetime.timedelta(days=1)
    with open('flights_table.json', mode='w', encoding='UTF8') as fp:
        json.dump(result, fp, ensure_ascii=False, sort_keys=False)


if __name__ == "__main__":
    today = datetime.date.today()
    create_flight_table(today)
