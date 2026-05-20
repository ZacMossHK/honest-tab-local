import socket
from datetime import datetime
from reflex.vars import NumberVar, var_operation, var_operation_return
from zoneinfo import ZoneInfo
from obhonesty.constants import SYSTEM_PROVIDER_HANDLING_FEE
from uuid import uuid4


@var_operation
def two_decimal_points(value: NumberVar):
    """This function will return the value with two decimal points."""
    return var_operation_return(
        js_expression=f"({value}.toFixed(2))",
        var_type=str,
    )


def generate_uuid():
    return str(uuid4())


def check_internet_connection():
    try:
        socket.create_connection(("www.google.com", 443), timeout=3)
    except OSError:
        print(f"No internet connection - {get_madrid_datetime_now()}", flush=True)
        raise


def get_model_string_type_columns(model) -> list[str]:
    string_type_columns = []

    for col in model.__table__.columns:
        if str(col.type) != "VARCHAR":
            continue

        string_type_columns.append(col.name)

    return string_type_columns


def sanitise_record_strings(string_type_columns, record):
    for key in record:
        if not key in string_type_columns:
            continue

        record[key] = str(record[key])
    return record


def generate_receiver_from_names(first_name, last_name):
    return f"{first_name.upper().strip()} {last_name.upper().strip()}"


def get_madrid_datetime_now():
    return datetime.now(ZoneInfo("Europe/Madrid"))


def get_todays_date_as_string():
    return get_madrid_datetime_now().date().strftime("%d/%m/%Y")


def generate_line_item(name: str, unit_amount: int, quantity: int):
    return {
        "price_data": {
            "currency": "eur",
            "product_data": {"name": name},
            "unit_amount": unit_amount,
        },
        "quantity": quantity,
    }


def get_system_provider_handling_fee_rounded_to_two_digits(amount):
    return round(amount * SYSTEM_PROVIDER_HANDLING_FEE, 2)


def get_full_breakfast_item(diet: str):
    return f"Breakfast sign-up ({diet})"
