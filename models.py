
from pony.orm import Database, Required, Json, Optional

from _settings import DB_CONFIG


db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    """Состояние пользователя внутри сценария"""
    user_id = Required(str, unique=True)
    scenario_name = Required(str)
    step_name = Required(str)
    context = Required(Json)


class Registration(db.Entity):
    """Заявка на регистрацию"""
    name = Required(str)
    email = Required(str)


class Flight(db.Entity):
    """оформление билета"""
    city_from = Required(str)
    city_to = Required(str)
    flight_date = Required(str)
    flight_number = Required(str)
    seats = Required(str)
    comments = Optional(str)
    phone = Required(str)


db.generate_mapping(create_tables=True)
