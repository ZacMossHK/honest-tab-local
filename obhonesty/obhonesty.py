from datetime import datetime
import reflex as rx
from sqlalchemy import select, or_
import asyncio
from obhonesty.pages import *
from obhonesty.state import State
from obhonesty.sheet import (
    user_sheet,
    item_sheet,
    order_sheet,
    admin_sheet,
    stripe_payments_sheet,
    payments_sheet,
    checkouts_sheet,
)
from obhonesty.models import (
    User,
    Order,
    Item,
    Admin,
    Meal,
    Stripe_Checkout_Session,
    Payment,
    Checkout,
)
from obhonesty.aux import (
    check_internet_connection,
    get_model_string_type_columns,
    sanitise_record_strings,
    generate_uuid,
    generate_receiver_from_names,
    get_madrid_datetime_now,
    get_todays_date_as_string,
)
import os
from fastapi import FastAPI, status
from typing import TypedDict
from gspread import Cell
from zoneinfo import ZoneInfo


class UnsyncedUserWithRow(TypedDict):
    row: int
    user: User


is_test_environment = True if os.getenv("TEST") else False
fastapi_app = FastAPI(title="Honesty Bar API")
app = rx.App() if not is_test_environment else rx.App(api_transformer=fastapi_app)
app.add_page(
    index,
    route="/",
    on_load=State.load_index_page,
)
app.add_page(
    user_page,
    route="/user",
    on_load=[
        State.clear_temp_state_values,
        State.check_user_is_still_active,
        State.reload_sheet_data,
    ],
)
app.add_page(user_signup_page, route="/signup")
app.add_page(
    dinner_signup_page,
    route="/dinner",
    on_load=State.update_last_user_activity_datetime,
)
app.add_page(
    breakfast_signup_page,
    route="/breakfast",
    on_load=State.update_last_user_activity_datetime,
)
app.add_page(
    custom_item_page,
    route="/custom_item",
    on_load=State.update_last_user_activity_datetime,
)
app.add_page(
    user_info_page,
    route="/info",
    on_load=[State.reload_sheet_data, State.update_last_user_activity_datetime],
)
app.add_page(
    admin,
    route="/admin",
    on_load=[State.clear_temp_state_values, State.reload_admin_dinner_data],
)
app.add_page(
    admin_dinner, route="/admin/dinner", on_load=State.reload_admin_dinner_data
)
app.add_page(
    admin_breakfast, route="/admin/breakfast", on_load=State.reload_admin_dinner_data
)
app.add_page(
    late_dinner_signup_page,
    route="/admin/late",
)


@fastapi_app.post("/api/test/user", status_code=status.HTTP_201_CREATED)
async def create_test_user(
    username: str, volunteer: str = "", prepaid_dinners_quantity=0
):
    with rx.session() as session:
        session.add(
            User.model_validate(
                {
                    "nick_name": username,
                    "first_name": username,
                    "last_name": "Test",
                    "phone_number": "0123456789",
                    "email": "test@test.com",
                    "diet": "Vegan",
                    "allergies": "Nuts",
                    "is_current_guest": True,
                    "is_synced": False,
                    "volunteer": len(volunteer) > 0,
                    "away": False,
                    "prepaid_dinners_quantity": prepaid_dinners_quantity,
                }
            )
        )
        session.commit()
    return {"username": username, "message": "Test user created successfully"}


@fastapi_app.get("/api/test/checkout")
async def get_checkout(username: str):
    checkout = rx.session().query(Checkout).filter(Checkout.user == username).first()
    return {"checkout": checkout.model_dump()}


@fastapi_app.get("/api/test/user")
async def get_user(
    username: str,
):
    user = rx.session().query(User).filter(User.nick_name == username).first()
    return {"user": user.model_dump()}


@fastapi_app.post("/api/test/orders", status_code=status.HTTP_201_CREATED)
async def create_test_order(
    order_id: str,
    user_nick_name: str,
    time: str,
    item: str,
    quantity: float,
    price: float,
    total: float,
    receiver: str,
    diet: str,
    allergies: str,
    served: str,
    tax_category: str,
    comment: str,
):
    with rx.session() as session:
        session.add(
            Order(
                order_id=order_id,
                user_nick_name=user_nick_name,
                time=time,
                item=item,
                quantity=quantity,
                price=price,
                total=total,
                receiver=receiver,
                diet=diet,
                allergies=allergies,
                served=served,
                tax_category=tax_category,
                comment=comment,
            )
        )
        session.commit()
    return {"order_id": order_id, "message": "Test order created successfully"}


@fastapi_app.get("/api/test/orders")
async def get_test_orders(username: str):
    with rx.session() as session:
        orders = session.query(Order).filter(Order.user_nick_name == username).all()
        return {"orders": [order.model_dump() for order in orders]}


@fastapi_app.get("/api/test/stripe-checkout-sessions")
async def get_stripe_checkout_sessions(username: str):
    with rx.session() as session:
        checkout_sessions = (
            session.query(Stripe_Checkout_Session)
            .filter(Stripe_Checkout_Session.user == username)
            .all()
        )
        return {
            "checkout_sessions": [
                checkout_session.model_dump() for checkout_session in checkout_sessions
            ]
        }


@fastapi_app.get("/api/test/payments")
async def get_payment(order_id: str):
    with rx.session() as session:
        payment = session.query(Payment).filter(Payment.order_id == order_id).first()
    return {"payment": payment.model_dump() if payment else "None found"}


@fastapi_app.get("/api/test/meals/dinner/today")
async def get_todays_dinner_meals():
    with rx.session() as session:
        todays_dinner_meals = (
            session.execute(Meal.select_todays_dinner_meals()).scalars().all()
        )
    return {"meals": [row.model_dump() for row in todays_dinner_meals]}


@fastapi_app.post("/api/test/meals/dinner/today", status_code=status.HTTP_201_CREATED)
async def create_dinner_meal_for_today(username: str, receiver: str):
    meal_id = generate_uuid()
    with rx.session() as session:
        session.add(
            Meal(
                meal_id=meal_id,
                order_id=generate_uuid(),
                user_nick_name=username,
                receiver=receiver,
                order_time=get_madrid_datetime_now(),
                meal_type="dinner",
                diet="Meat",
                allergies="",
                volunteer=False,
                served=False,
            )
        )
        session.commit()
    return {"meal_id": meal_id, "message": "Test meal created successfully"}


@fastapi_app.post("/api/test/stripe/trigger")
async def trigger_stripe_session_response(stripe_test_state: str, token: str):
    async with app.modify_state(token) as root_state:
        state = await root_state.get_state(State)
        state.stripe_test_state = stripe_test_state


@fastapi_app.get("/api/test/stripe/line-items")
async def get_stripe_line_items(token: str):
    async with app.modify_state(token) as root_state:
        state = await root_state.get_state(State)
        return {"line_items": state.test_line_items}


def get_records(sheet, headers: list[str] = [], add_synced: bool = False):
    check_internet_connection()
    if sheet is None:
        return []
    records = sheet.get_all_records(expected_headers=headers)

    for record in records:
        if "" in record:
            del record[""]

    return (
        [{**record, "is_synced": True} for record in records] if add_synced else records
    )


def sync_new_orders(unsynced_orders):
    new_rows = []
    for order in unsynced_orders:
        new_rows.append(
            [
                order.order_id,
                order.user_nick_name,
                order.time,
                order.item,
                order.quantity,
                order.price,
                order.total,
                order.receiver,
                order.diet,
                order.allergies,
                order.served,
                order.tax_category,
                order.comment,
            ]
        )
    order_sheet.append_rows(
        new_rows, value_input_option="USER_ENTERED", table_range="A1"
    )


def sync_new_users(unsynced_users: list[User]):
    new_rows = []
    for user in unsynced_users:
        new_rows.append(
            [
                user.nick_name,
                user.first_name,
                user.last_name,
                user.phone_number,
                user.email,
                user.diet,
                user.allergies,
                user.volunteer,
                user.away,
                "",
                user.is_current_guest,
                user.has_active_tab,
                user.prepaid_dinners_quantity if user.prepaid_dinners_quantity else "",
            ]
        )
    user_sheet.append_rows(
        new_rows, value_input_option="USER_ENTERED", table_range="A1"
    )


def sync_updated_users(unsynced_users_with_rows: list[UnsyncedUserWithRow]):
    updated_cells: list[Cell] = []
    for unsynced_user_with_row in unsynced_users_with_rows:
        for column_number, column_name in [
            [12, "has_active_tab"],
            [13, "prepaid_dinners_quantity"],
        ]:
            value = getattr(unsynced_user_with_row["user"], column_name)
            if column_name == "prepaid_dinners_quantity" and not value:
                value = ""
            updated_cells.append(
                Cell(
                    row=unsynced_user_with_row["row"],
                    col=column_number,
                    value=value,
                )
            )
    user_sheet.update_cells(updated_cells, value_input_option="USER_ENTERED")


def add_google_sheet_data_to_session(session, google_sheet_data, model, id_column_name):
    string_column_names = get_model_string_type_columns(model)
    for index, record in enumerate(google_sheet_data):
        try:
            if record[id_column_name] == "":
                raise Exception(f"id column '{id_column_name}' is blank")
            for column_name in record:
                if column_name not in string_column_names:
                    continue
                record[column_name] = str(record[column_name])
            session.add(model.model_validate(record))
        except Exception as e:
            id = record[id_column_name] if record[id_column_name] != "" else "N/A"
            print(
                f"Unable to add {model.__name__} {id} on row {index + 2}: {e}\nRecord: {record}",
                flush=True,
            )


def sync_orders():
    try:
        order_string_columns = get_model_string_type_columns(Order)

        with rx.session() as session:
            order_data = get_records(
                order_sheet,
                [
                    "order_id",
                    "user",
                    "time",
                    "item",
                    "quantity",
                    "price",
                    "total",
                    "diet",
                    "allergies",
                    "served",
                    "tax_category",
                    "comment",
                ],
                True,
            )
            current_unsynced_orders = (
                session.query(Order).filter(~Order.is_synced).all()
            )
            if not len(current_unsynced_orders):
                for order in order_data:
                    order["user_nick_name"] = order["user"]
                    del order["user"]
                    sanitise_record_strings(order_string_columns, order)
                for row in session.exec(Order.select()).all():
                    session.delete(row)
                add_google_sheet_data_to_session(session, order_data, Order, "order_id")

            google_sheet_order_ids = [order["order_id"] for order in order_data]
            remaining_unsynced_orders = []

            for order in current_unsynced_orders:
                if order.order_id in google_sheet_order_ids:
                    order.is_synced = True
                    continue
                remaining_unsynced_orders.append(order)

            session.commit()
            if len(remaining_unsynced_orders):
                sync_new_orders(remaining_unsynced_orders)
    except Exception as e:
        print(f"sync_orders error: {e}")


def sync_users():
    try:
        with rx.session() as session:
            google_sheets_user_data = get_records(
                user_sheet,
                [
                    "nick_name",
                    "first_name",
                    "last_name",
                    "phone_number",
                    "email",
                    "diet",
                    "allergies",
                    "volunteer",
                    "away",
                    "owes",
                    "is_current_guest",
                    "has_active_tab",
                    "prepaid_dinners_quantity",
                ],
                True,
            )
            current_unsynced_users: list[User] = (
                session.query(User).filter(~User.is_synced).all()
            )
            new_unsynced_users_to_sync: list[User] = []
            updated_unsynced_users_to_sync: list[UnsyncedUserWithRow] = []

            for google_sheets_user in google_sheets_user_data:
                del google_sheets_user["owes"]
                for key in ["volunteer", "away", "is_current_guest", "has_active_tab"]:
                    google_sheets_user[key] = google_sheets_user[key].lower() in [
                        "yes",
                        "true",
                    ]
                google_sheets_user = sanitise_record_strings(
                    get_model_string_type_columns(User), google_sheets_user
                )
                google_sheets_user["prepaid_dinners_quantity"] = (
                    0
                    if google_sheets_user["prepaid_dinners_quantity"] == ""
                    else int(google_sheets_user["prepaid_dinners_quantity"])
                )

            if not len(current_unsynced_users):
                for row in session.exec(User.select()).all():
                    session.delete(row)
                add_google_sheet_data_to_session(
                    session, google_sheets_user_data, User, "nick_name"
                )

            else:
                google_sheet_user_nick_names: list[str] = [
                    google_sheets_user["nick_name"]
                    for google_sheets_user in google_sheets_user_data
                ]

                for unsynced_user in current_unsynced_users:
                    if unsynced_user.nick_name not in google_sheet_user_nick_names:
                        new_unsynced_users_to_sync.append(unsynced_user)
                        continue
                    matching_google_sheet_user_index = (
                        google_sheet_user_nick_names.index(unsynced_user.nick_name)
                    )
                    matching_google_sheet_user = google_sheets_user_data[
                        matching_google_sheet_user_index
                    ]
                    if not all(
                        matching_google_sheet_user[column]
                        == getattr(unsynced_user, column)
                        for column in [
                            "has_active_tab",
                            "prepaid_dinners_quantity",
                        ]
                    ):
                        updated_unsynced_users_to_sync.append(
                            {
                                "row": matching_google_sheet_user_index + 2,
                                "user": unsynced_user,
                            }
                        )
                        continue
                    unsynced_user.is_synced = True

            session.commit()
            if len(new_unsynced_users_to_sync):
                sync_new_users(new_unsynced_users_to_sync)
            if len(updated_unsynced_users_to_sync):
                sync_updated_users(updated_unsynced_users_to_sync)
    except Exception as e:
        print(f"sync_users error: {e}")


def sync_items():
    try:
        with rx.session() as session:
            item_data = get_records(
                item_sheet, ["name", "price", "description", "tax_category"]
            )

            for row in session.exec(Item.select()).all():
                session.delete(row)

            add_google_sheet_data_to_session(session, item_data, Item, "name")

            # seeds a test item for e2e testing if it doesn't already exist
            if is_test_environment:
                test_item_exists = False

                for item in item_data:
                    if item["name"] != "TEST ITEM":
                        continue
                    test_item_exists = True
                    break

                if not test_item_exists:
                    session.add(
                        Item.model_validate(
                            {
                                "name": "TEST ITEM",
                                "price": 1.0,
                                "description": "",
                                "tax_category": "Miscellaneous",
                                "icon": "",
                            }
                        )
                    )

            session.commit()
    except Exception as e:
        print(f"sync_items error: {e}")


def sync_admin_data():
    try:
        with rx.session() as session:
            admin_data = get_records(admin_sheet)[0]
            for row in session.exec(Admin.select()).all():
                session.delete(row)
            add_google_sheet_data_to_session(
                session,
                [{"key": key, "value": str(admin_data[key])} for key in admin_data],
                Admin,
                "key",
            )
            session.commit()
    except Exception as e:
        print(f"sync_admin_data error: {e}")


def update_meals_table():
    try:
        with rx.session() as session:
            now = get_madrid_datetime_now()
            # if a meal doesn't have a corresponding order then the order will have been deleted by staff, so it should be removed
            todays_guest_meals_without_corresponding_orders: list[Meal] = (
                session.execute(
                    Meal.select_todays_meals().where(
                        Meal.order_id != "N/A",
                        Meal.order_id.notin_(
                            select(Order.order_id).where(
                                Order.time.ilike(f"{get_todays_date_as_string()}%"),
                                or_(
                                    Order.item == "Breakfast sign-up",
                                    Order.item.ilike("Dinner sign-up%"),
                                ),
                            )
                        ),
                    )
                ).scalars()
            )
            for meal in todays_guest_meals_without_corresponding_orders:
                session.delete(meal)
            dinner_meals_today_as_receivers: set[str] = set(
                session.execute(
                    Meal.select_todays_dinner_meals().with_only_columns(Meal.receiver)
                )
                .scalars()
                .all()
            )
            volunteers: list[User] = (
                session.exec(
                    select(User).where(
                        User.volunteer == True, User.is_current_guest == True
                    )
                )
                .scalars()
                .all()
            )
            # add volunteer meals to tonight's dinner list if they have not already been added
            for volunteer in volunteers:
                volunteer_receiver_name = generate_receiver_from_names(
                    volunteer.first_name, volunteer.last_name
                )
                if volunteer_receiver_name in dinner_meals_today_as_receivers:
                    continue
                session.add(
                    Meal(
                        meal_id=generate_uuid(),
                        order_id="N/A",
                        user_nick_name=volunteer.nick_name,
                        receiver=volunteer_receiver_name,
                        order_time=now,
                        meal_type="dinner",
                        diet=volunteer.diet,
                        allergies=volunteer.allergies,
                        volunteer=True,
                        served=False,
                    )
                )
            volunteers_as_receivers = set(
                generate_receiver_from_names(volunteer.first_name, volunteer.last_name)
                for volunteer in volunteers
            )
            # remove dinner meals for volunteers who have recently left
            for dinner_meal in session.execute(
                Meal.select_todays_dinner_meals().where(Meal.volunteer == True)
            ).scalars():
                if dinner_meal.receiver in volunteers_as_receivers:
                    continue
                session.delete(dinner_meal)
            # add new orders to today's meals if not already added
            signups_in_todays_orders: list[Order] = session.execute(
                select(Order).where(
                    Order.time.ilike(f"{get_todays_date_as_string()}%"),
                    or_(
                        Order.item == "Breakfast sign-up",
                        Order.item.ilike("Dinner sign-up%"),
                    ),
                    Order.order_id.notin_(
                        Meal.select_todays_meals().with_only_columns(Meal.order_id)
                    ),
                )
            ).scalars()
            for order in signups_in_todays_orders:
                session.add(
                    Meal(
                        meal_id=generate_uuid(),
                        order_id=order.order_id,
                        user_nick_name=order.user_nick_name,
                        receiver=order.receiver,
                        order_time=datetime.strptime(
                            order.time, DATETIME_FORMAT
                        ).replace(tzinfo=ZoneInfo("Europe/Madrid")),
                        meal_type=(
                            "breakfast"
                            if order.item == "Breakfast sign-up"
                            else "dinner"
                        ),
                        diet=order.diet,
                        allergies=order.allergies,
                        volunteer=False,
                        served=False,
                    )
                )
            session.commit()
    except Exception as e:
        print(f"update_meal_table error: {e}")


def sync_new_stripe_checkout_sessions():
    try:
        stripe_checkout_session_records = get_records(
            stripe_payments_sheet,
            [
                "payment_order_id",
                "datetime_requested",
                "stripe_payment_id",
                "ob_payment_id",
                "order_id",
                "user",
                "system_provider_handling_fee_amount",
                "item",
                "quantity",
                "price",
                "total",
            ],
        )
        stripe_checkout_session_record_payment_ids: set[str] = set(
            checkout_session["payment_order_id"]
            for checkout_session in stripe_checkout_session_records
        )

        with rx.session() as session:
            remaining_unsynced_sessions: list[Stripe_Checkout_Session] = []
            unsynced_stripe_checkout_session_rows = (
                session.query(Stripe_Checkout_Session)
                .filter(~Stripe_Checkout_Session.is_synced)
                .all()
            )

            for unsynced_session in unsynced_stripe_checkout_session_rows:
                if (
                    unsynced_session.payment_order_id
                    in stripe_checkout_session_record_payment_ids
                ):
                    unsynced_session.is_synced = True
                    continue
                remaining_unsynced_sessions.append(unsynced_session)

            if len(remaining_unsynced_sessions):
                stripe_payments_sheet.append_rows(
                    [
                        [
                            remaining_unsynced_session.payment_order_id,
                            remaining_unsynced_session.datetime_requested,
                            remaining_unsynced_session.stripe_payment_id,
                            remaining_unsynced_session.ob_payment_id,
                            remaining_unsynced_session.order_id,
                            remaining_unsynced_session.user,
                            remaining_unsynced_session.system_provider_handling_fee_amount,
                            remaining_unsynced_session.item,
                            remaining_unsynced_session.quantity,
                            remaining_unsynced_session.price,
                            remaining_unsynced_session.total,
                            remaining_unsynced_session.receiver,
                            remaining_unsynced_session.diet,
                            remaining_unsynced_session.allergies,
                            remaining_unsynced_session.tax_category,
                            remaining_unsynced_session.comment,
                        ]
                        for remaining_unsynced_session in remaining_unsynced_sessions
                    ],
                    value_input_option="USER_ENTERED",
                    table_range="A1",
                )
            session.commit()

    except Exception as e:
        print(f"sync_new_stripe_checkout_sessions error: {e}")


def sync_payments():
    try:
        payment_data = get_records(
            payments_sheet,
            [
                "payment_id",
                "order_id",
                "paid_time",
                "method",
                "checkout_staff",
            ],
            True,
        )
        payment_ids: set[str] = set(payment["payment_id"] for payment in payment_data)

        with rx.session() as session:
            unsynced_payments: list[Payment] = (
                session.query(Payment).filter(~Payment.is_synced).all()
            )
            remaining_unsynyced_payments: list[Payment] = []
            for unsynced_payment in unsynced_payments:
                if unsynced_payment.payment_id in payment_ids:
                    unsynced_payment.is_synced = True
                    continue
                remaining_unsynyced_payments.append(unsynced_payment)

            session.commit()
            if len(remaining_unsynyced_payments):
                payments_sheet.append_rows(
                    [
                        [
                            unsynced_payment.payment_id,
                            unsynced_payment.order_id,
                            datetime.strftime(
                                unsynced_payment.paid_time.astimezone(
                                    ZoneInfo("Europe/Madrid")
                                ),
                                DATETIME_FORMAT,
                            ),
                            unsynced_payment.method,
                            unsynced_payment.checkout_staff,
                        ]
                        for unsynced_payment in remaining_unsynyced_payments
                    ],
                    value_input_option="USER_ENTERED",
                    table_range="A1",
                )
                return

            for row in session.exec(Payment.select()).all():
                session.delete(row)
            for index, payment in enumerate(payment_data):
                payment_data[index]["paid_time"] = datetime.strptime(
                    payment_data[index]["paid_time"], DATETIME_FORMAT
                ).replace(tzinfo=ZoneInfo("Europe/Madrid"))
            add_google_sheet_data_to_session(
                session, payment_data, Payment, "payment_id"
            )
            session.commit()
    except Exception as e:
        print(f"sync_payments error: {e}")


def sync_checkouts():
    try:
        checkout_data = get_records(
            checkouts_sheet,
            [
                "checkout_id",
                "user",
                "checkout_datetime",
                "checkout_origin",
                "checkout_origin_payment_id",
            ],
            True,
        )
        checkout_ids: set[str] = set(
            checkout["checkout_id"] for checkout in checkout_data
        )

        with rx.session() as session:
            unsynced_checkouts: list[Checkout] = (
                session.query(Checkout).filter(~Checkout.is_synced).all()
            )
            remaining_unsynyced_checkouts: list[Checkout] = []
            for unsynced_checkout in unsynced_checkouts:
                if unsynced_checkout.checkout_id in checkout_ids:
                    unsynced_checkout.is_synced = True
                    continue
                remaining_unsynyced_checkouts.append(unsynced_checkout)

            session.commit()
            if len(remaining_unsynyced_checkouts):
                checkouts_sheet.append_rows(
                    [
                        [
                            unsynced_checkout.checkout_id,
                            unsynced_checkout.user,
                            datetime.strftime(
                                unsynced_checkout.checkout_datetime.astimezone(
                                    ZoneInfo("Europe/Madrid")
                                ),
                                DATETIME_FORMAT,
                            ),
                            unsynced_checkout.checkout_origin,
                            unsynced_checkout.checkout_origin_payment_id,
                        ]
                        for unsynced_checkout in remaining_unsynyced_checkouts
                    ],
                    value_input_option="USER_ENTERED",
                    table_range="A1",
                )
                return

            for row in session.exec(Checkout.select()).all():
                session.delete(row)
            for index, checkout in enumerate(checkout_data):
                checkout_data[index]["checkout_datetime"] = datetime.strptime(
                    checkout_data[index]["checkout_datetime"], DATETIME_FORMAT
                ).replace(tzinfo=ZoneInfo("Europe/Madrid"))
            add_google_sheet_data_to_session(
                session, checkout_data, Checkout, "checkout_id"
            )
            session.commit()
    except Exception as e:
        print(f"sync_checkouts error: {e}")


async def run_loop_tasks():
    while True:
        try:
            update_meals_table()
            await asyncio.sleep(5)
            sync_orders()
            await asyncio.sleep(5)
            sync_users()
            await asyncio.sleep(5)
            sync_items()
            await asyncio.sleep(5)
            sync_admin_data()
            await asyncio.sleep(5)
            sync_new_stripe_checkout_sessions()
            await asyncio.sleep(5)
            sync_payments()
            await asyncio.sleep(5)
            sync_checkouts()
        except Exception as e:
            print(f"run_loop_tasks error: {e}")
        await asyncio.sleep(10)


app.register_lifespan_task(run_loop_tasks)
