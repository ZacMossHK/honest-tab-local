from datetime import datetime, timedelta, UTC
import asyncio
from typing import Any, Dict, List, Optional, Literal
from urllib.parse import quote
import reflex as rx
import stripe
from sqlalchemy import update, select, exists
from dotenv import load_dotenv
import os
from obhonesty.aux import (
    generate_uuid,
    generate_receiver_from_names,
    check_internet_connection,
    get_madrid_datetime_now,
    generate_line_item,
    get_system_provider_handling_fee_rounded_to_two_digits,
    get_full_breakfast_item,
)
from obhonesty.constants import DATETIME_FORMAT
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
from zoneinfo import ZoneInfo

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
is_test_environment = True if os.getenv("TEST") else False


class State(rx.State):
    """The app state."""

    has_sheet_data_finished_fetching: bool = False
    admin_data: Dict[str, Any] = {}
    users: List[User] = []
    items: Dict[str, Item] = {}
    todays_breakfast_meals: List[Meal] = []
    todays_dinner_meals: List[Meal] = []
    current_user: Optional[User] = None
    new_nick_name: str = ""
    custom_item_price: str = ""
    is_item_button_dialog_active: bool = False
    ordered_item: str = ""
    is_closing_account: Optional[bool] = None
    is_email_login_incorrect = False
    late_dinner_user_nick_name: Optional[str] = None
    late_dinner_diet: str = ""
    show_stripe_connection_failure_message = False
    show_stripe_timeout_message = False
    has_stripe_qr_generation_failed = False
    should_late_dinner_signup_form_reload = False
    item_uuid: str = ""
    is_logging_user_in: bool = False
    is_user_activity_check_running: bool = False
    latest_user_activity_datetime: datetime = None
    is_reload_admin_dinner_data_running: bool = False
    current_user_orders: list[Order] = []
    are_payments_enabled: bool = True
    last_reload_time: datetime = get_madrid_datetime_now()

    # --- Test Environment State ---
    stripe_test_state: Literal["success"] | None = None
    test_line_items = []

    # --- Meal Counts ---

    breakfast_count: int = 0
    breakfast_count_served: int = 0

    dinner_count: int = 0
    dinner_count_served: int = 0

    dinner_count_vegan: int = 0
    dinner_count_vegetarian: int = 0
    dinner_count_meat: int = 0

    dinner_count_guests: int = 0
    dinner_count_guests_served: int = 0
    dinner_count_guests_vegan: int = 0
    dinner_count_guests_vegetarian: int = 0
    dinner_count_guests_meat: int = 0

    dinner_count_volunteers: int = 0
    dinner_count_volunteers_served: int = 0
    dinner_count_volunteers_vegan: int = 0
    dinner_count_volunteers_vegetarian: int = 0
    dinner_count_volunteers_meat: int = 0

    is_loading_admin_meal_table: bool = True
    optimistic_served_states: dict[str, bool] = {}

    # --- Payment State Variables ---
    current_stripe_session_id: str = ""
    payment_qr_code: str = ""
    is_stripe_session_paid: bool = False
    is_stripe_dialog_active: bool = False
    is_payment_status_written_to_db: bool = False
    stripe_system_provider_handling_fee_amount: float = 0
    stripe_total: float = 0
    ob_payment_id: str = ""
    # ------------------------------------

    # --- Item Payment State ---
    temp_quantity: float = 1.0

    # --- Signup button state
    order_request_id: str = ""
    current_order_request_id: str = ""

    # --- Breakfast state ---
    breakfast_signup_first_name: str = ""
    breakfast_signup_last_name: str = ""
    breakfast_signup_item: str = ""
    breakfast_signup_allergies: str = ""

    # --- Dinner State ---
    dinner_signup_first_name: str = ""
    dinner_signup_last_name: str = ""
    dinner_signup_dietary_preference: str = ""
    dinner_signup_allergies: str = ""
    # -----------------------------

    @rx.event
    def load_index_page(self):
        self.handle_user_reset()
        self.reset_stripe_dialog_active_state()
        self.clear_temp_state_values()
        return State.loop_reload_sheet_data_on_index_page

    @rx.event
    def is_client_still_connected(self):
        # importing here avoids a circular import error
        from obhonesty.obhonesty import app

        return self.router.session.client_token in app.event_namespace.token_to_sid

    @rx.event(background=True)
    async def loop_reload_sheet_data_on_index_page(self):
        while self.router.page.path == ("/index"):
            if not self.is_client_still_connected():
                break
            async with self:
                self.reload_sheet_data()
            await asyncio.sleep(10)

    @rx.event
    def redirect_to_homepage(self):
        self.has_sheet_data_finished_fetching = False
        return rx.redirect("/")

    def set_temp_quantity(self, value: str):
        try:
            self.temp_quantity = float(value)
        except ValueError:
            self.temp_quantity = 1.0

    @rx.var(cache=False)
    def is_order_request_loading(self) -> bool:
        return self.current_order_request_id != ""

    @rx.event
    def set_order_request_id(self):
        request_id = generate_uuid()
        self.order_request_id = request_id
        if self.current_order_request_id != "":
            return
        self.current_order_request_id = request_id

    @rx.event
    def set_late_dinner_diet(self, value: str):
        self.late_dinner_diet = value

    @rx.event
    def redirect_to_later_dinner_signup(self):
        self.late_dinner_diet = ""
        self.late_dinner_user_nick_name = ""
        return rx.redirect("/admin/late")

    @rx.event
    def reset_order_request_id(self):
        self.order_request_id = ""
        self.current_order_request_id = ""

    def set_breakfast_signup_default_values(self):
        self.breakfast_signup_first_name = self.current_user.first_name
        self.breakfast_signup_last_name = self.current_user.last_name
        self.breakfast_signup_item = ""
        self.breakfast_signup_allergies = self.current_user.allergies

    def set_breakfast_signup_first_name(self, value: str):
        self.breakfast_signup_first_name = value.strip()

    def set_breakfast_signup_last_name(self, value: str):
        self.breakfast_signup_last_name = value.strip()

    def set_breakfast_signup_item(self, value: str):
        self.breakfast_signup_item = value

    def set_breakfast_signup_allergies(self, value: str):
        self.breakfast_signup_allergies = value.strip()

    def set_dinner_signup_first_name(self, value: str):
        self.dinner_signup_first_name = value.strip()

    def set_dinner_signup_last_name(self, value: str):
        self.dinner_signup_last_name = value.strip()

    def set_dinner_dietary_preference(self, value: str):
        self.dinner_signup_dietary_preference = value

    def set_dinner_allergies(self, value: str):
        self.dinner_signup_allergies = value.strip()

    def set_dinner_signup_default_values(self):
        self.dinner_signup_first_name = (
            self.current_user.first_name if self.current_user else ""
        )
        self.dinner_signup_last_name = (
            self.current_user.last_name if self.current_user else ""
        )
        self.dinner_signup_dietary_preference = (
            self.current_user.diet if self.current_user else ""
        )
        self.dinner_signup_allergies = (
            self.current_user.allergies if self.current_user else ""
        )

    @rx.event
    def reset_stripe_dialog_active_state(self):
        self.is_stripe_dialog_active = False
        self.current_order_request_id = ""

    @rx.event
    def expire_stripe_session(self):
        if not is_test_environment:
            try:
                stripe.checkout.Session.expire(self.current_stripe_session_id)

            except Exception as e:
                # this message means the transaction was successful or has already expired so we should ignore it
                if (
                    'Only Checkout Sessions with a status in ["open"] can be expired.'
                    not in str(e)
                ):
                    print(
                        f"Error expiring Stripe session: {e} - {get_madrid_datetime_now()}",
                        flush=True,
                    )

        self.current_stripe_session_id = ""

    @rx.event
    def clear_temp_state_values(self):
        self.is_item_button_dialog_active = False
        self.dinner_signup_first_name = ""
        self.dinner_signup_last_name = ""
        self.dinner_signup_dietary_preference = ""
        self.dinner_signup_allergies = ""
        self.breakfast_signup_first_name = ""
        self.breakfast_signup_last_name = ""
        self.breakfast_signup_item = ""
        self.dinner_signup_allergies = ""
        if self.current_stripe_session_id != "":
            self.expire_stripe_session()
        self.payment_qr_code = ""
        self.is_stripe_session_paid = False
        self.is_payment_status_written_to_db = False
        self.is_closing_account = None
        self.show_stripe_connection_failure_message = False
        self.has_stripe_qr_generation_failed = False

        if self.is_stripe_dialog_active and not self.is_logging_user_in:
            # unblocks item buttons if the page is navigated away from before item payment is completed
            self.is_stripe_dialog_active = False
            self.current_order_request_id = ""

        self.is_logging_user_in = False

    @rx.event(background=True)
    async def set_served(self, meal_id: str, value: bool):
        async with self:
            self.optimistic_served_states[meal_id] = value
        try:
            with rx.session() as session:
                session.exec(
                    update(Meal).where(Meal.meal_id == meal_id).values(served=value)
                )
                session.commit()
            async with self:
                self.update_meal_totals()
        except:
            async with self:
                self.optimistic_served_states[meal_id] = not value
            return rx.toast.error(
                "Could not mark this meal as served, please try again."
            )

    def set_dinner_as_ordered_item(self):
        self.ordered_item = "dinner"

    @rx.event
    def set_late_dinner_user_nick_name(self, nick_name: str):
        self.late_dinner_user_nick_name = nick_name

    @rx.event
    def reset_late_dinner_user_nick_name(self):
        self.late_dinner_user_nick_name = None
        self.late_dinner_diet = ""

    @rx.event
    def handle_user_reset(self):
        self.current_user = None

    @rx.event
    def update_last_user_activity_datetime(self):
        self.latest_user_activity_datetime = get_madrid_datetime_now()

    @rx.event(background=True)
    async def check_user_is_still_active(self):
        async with self:
            self.update_last_user_activity_datetime()
            if self.is_user_activity_check_running:
                return
            self.is_user_activity_check_running = True
        has_timeout_toast_displayed = False

        while self.is_user_activity_check_running:
            if not self.is_client_still_connected():
                break
            time_since_last_user_activity = (
                get_madrid_datetime_now() - self.latest_user_activity_datetime
            )
            should_user_be_shown_timeout_warning_toast = (
                time_since_last_user_activity >= timedelta(minutes=1, seconds=40)
            )
            if (
                should_user_be_shown_timeout_warning_toast
                and not has_timeout_toast_displayed
            ):
                yield rx.toast.warning(
                    "Are you still there? You will be logged out due to inactivity in twenty seconds.",
                    close_button=True,
                    position="bottom-center",
                    duration=20000,
                )
            has_timeout_toast_displayed = should_user_be_shown_timeout_warning_toast
            is_user_inactive_for_two_minutes = (
                time_since_last_user_activity >= timedelta(minutes=2)
            )
            if self.current_user is None or is_user_inactive_for_two_minutes:
                async with self:
                    self.is_user_activity_check_running = False
                if is_user_inactive_for_two_minutes:
                    yield State.redirect_to_homepage
                    break
            await asyncio.sleep(1)

    @rx.event
    def get_users_with_active_tabs(self):
        return rx.session().exec(User.select_users_with_an_active_tab()).scalars().all()

    @rx.event
    def get_todays_breakfast_meals(self):
        return (
            rx.session().execute(Meal.select_todays_breakfast_meals()).scalars().all()
        )

    @rx.event
    def get_todays_dinner_meals(self):
        return rx.session().execute(Meal.select_todays_dinner_meals()).scalars().all()

    @rx.event
    def get_admin_data(self):
        admin_data = {}
        for row in rx.session().exec(Admin.select()).all():
            if "deadline" in row.key:
                admin_data[row.key] = row.value
            elif row.key == "are_payments_enabled":
                admin_data[row.key] = row.value.lower() == "true"
                if not self.is_stripe_dialog_active:
                    self.are_payments_enabled = admin_data[row.key]
            else:
                admin_data[row.key] = float(row.value)
        return admin_data

    @rx.event
    def get_user(self, nick_name: str) -> User:
        return (
            rx.session().exec(select(User).where(User.nick_name == nick_name)).scalar()
        )

    @rx.event
    def update_current_user(self):
        if not self.current_user:
            return

        self.current_user = self.get_user(self.current_user.nick_name)

    @rx.event
    def reload_sheet_data(self):
        with rx.session() as session:
            items = {}
            for row in session.exec(Item.select()).all():
                if row.name == "":
                    continue
                items[row.name] = row
        self.items = items
        self.users = self.get_users_with_active_tabs()
        self.admin_data = self.get_admin_data()
        self.update_current_user()
        self.update_current_user_orders()
        if not self.has_sheet_data_finished_fetching:
            self.has_sheet_data_finished_fetching = True

    @rx.event
    def update_meal_totals(self):
        meal_totals = Meal.get_todays_meal_counts()
        self.breakfast_count = meal_totals["breakfast"]["total"]
        self.breakfast_count_served = meal_totals["breakfast"]["served"]

        self.dinner_count_guests_served = meal_totals["dinner"]["guest"]["served"]
        self.dinner_count_guests_vegan = meal_totals["dinner"]["guest"]["vegan"]
        self.dinner_count_guests_vegetarian = meal_totals["dinner"]["guest"][
            "vegetarian"
        ]
        self.dinner_count_guests_meat = meal_totals["dinner"]["guest"]["meat"]
        self.dinner_count_guests = (
            self.dinner_count_guests_vegan
            + self.dinner_count_guests_vegetarian
            + self.dinner_count_guests_meat
        )

        self.dinner_count_volunteers_served = meal_totals["dinner"]["volunteer"][
            "served"
        ]
        self.dinner_count_volunteers_vegan = meal_totals["dinner"]["volunteer"]["vegan"]
        self.dinner_count_volunteers_vegetarian = meal_totals["dinner"]["volunteer"][
            "vegetarian"
        ]
        self.dinner_count_volunteers_meat = meal_totals["dinner"]["volunteer"]["meat"]
        self.dinner_count_volunteers = (
            self.dinner_count_volunteers_vegan
            + self.dinner_count_volunteers_vegetarian
            + self.dinner_count_volunteers_meat
        )

        self.dinner_count = self.dinner_count_volunteers + self.dinner_count_guests
        self.dinner_count_served = (
            self.dinner_count_volunteers_served + self.dinner_count_guests_served
        )

        self.dinner_count_volunteers_vegan + self.dinner_count_guests_vegan
        self.dinner_count_vegetarian = (
            self.dinner_count_volunteers_vegetarian
            + self.dinner_count_guests_vegetarian
        )
        self.dinner_count_meat = (
            self.dinner_count_volunteers_meat + self.dinner_count_guests_meat
        )

    @rx.var
    def last_reload_time_formatted(self) -> str:
        return self.last_reload_time.strftime("%H:%M:%S %d/%m/%Y")

    @rx.event
    def restart_reload_admin_dinner_data_loop(self):
        self.is_reload_admin_dinner_data_running = False
        return State.reload_admin_dinner_data

    @rx.event(background=True)
    async def reload_admin_dinner_data(self):
        if self.is_reload_admin_dinner_data_running:
            return
        async with self:
            self.is_reload_admin_dinner_data_running = True
        while self.router.page.path.startswith("/admin"):
            if not self.is_client_still_connected():
                break
            async with self:
                self.last_reload_time = get_madrid_datetime_now()
                self.update_meal_totals()
                self.users = self.get_users_with_active_tabs()
                self.todays_breakfast_meals = self.get_todays_breakfast_meals()
                self.todays_dinner_meals = self.get_todays_dinner_meals()
                for meal in self.todays_breakfast_meals + self.todays_dinner_meals:
                    self.optimistic_served_states[meal.meal_id] = meal.served
                self.admin_data = self.get_admin_data()
                if self.is_loading_admin_meal_table:
                    self.is_loading_admin_meal_table = False
            await asyncio.sleep(3)

    @rx.event
    def handle_user_login_form_submit(self, form_data):
        user: Optional[User] = None
        error_message: Optional[str] = None

        try:
            user = (
                rx.session()
                .exec(select(User).where(User.nick_name == form_data["user_nick_name"]))
                .scalar()
            )

        except:
            error_message = (
                "There has been an error with your account. Please see reception."
            )

        if not user:
            error_message = "Your account could not be found. Please see reception."

        if error_message:
            return rx.toast.error(error_message)

        if (
            str(form_data["email_first_five_chars"])
            != user.email.replace("@", "").lower()[:5]
        ):
            self.is_email_login_incorrect = True
            return

        self.current_user = user
        self.is_user_activity_check_running = False
        self.is_email_login_incorrect = False
        self.is_logging_user_in = True
        return rx.redirect("/user")

    @rx.event
    def handle_user_login_dialog_open_change(self):
        self.is_email_login_incorrect = False

    @rx.event
    def handle_user_logout(self):
        return State.redirect_to_homepage

    @rx.event
    def redirect_no_user(self):
        if self.current_user is None:
            return State.redirect_to_homepage

    @rx.event
    def order_item(self):
        item = self.items[self.ordered_item]

        try:
            quantity = float(self.temp_quantity)

        except BaseException:
            return rx.toast.error("Failed to register. Quantity must be a number")

        now = get_madrid_datetime_now()

        with rx.session() as session:
            session.add(
                Order(
                    order_id=(
                        self.item_uuid
                        if self.is_stripe_session_paid
                        else generate_uuid()
                    ),
                    user_nick_name=self.current_user.nick_name,
                    time=now.strftime(DATETIME_FORMAT),
                    item=item.name,
                    quantity=quantity,
                    price=item.price,
                    total=quantity * item.price,
                    receiver="",
                    diet="",
                    allergies="",
                    served="",
                    tax_category=item.tax_category,
                    comment="",
                )
            )

            if self.is_stripe_session_paid:
                session.add(
                    Payment(
                        payment_id=generate_uuid(),
                        order_id=self.item_uuid,
                        paid_time=now,
                        method="stripe-tablet",
                        checkout_staff="",
                    )
                )

            session.commit()

        if self.is_stripe_session_paid:
            self.is_payment_status_written_to_db = True

        return rx.toast.info(
            f"'{item.name}' registered succesfully. Thank you!",
            position="bottom-center",
        )

    @rx.event
    def order_custom_item(self, form_data: dict):
        now = get_madrid_datetime_now().strftime(DATETIME_FORMAT)
        price = float(form_data["custom_item_price"])
        item_name = form_data["custom_item_name"]

        with rx.session() as session:
            session.add(
                Order(
                    order_id=generate_uuid(),
                    user_nick_name=self.current_user.nick_name,
                    time=now,
                    item=item_name,
                    quantity=1,
                    price=price,
                    total=price,
                    receiver="",
                    diet="",
                    allergies="",
                    served="",
                    tax_category=form_data["tax_category"],
                    comment=form_data["custom_item_description"],
                )
            )
            session.commit()

        return [
            rx.toast.info(
                f"'{item_name}' registered succesfully. Thank you!",
                position="bottom-center",
            ),
            rx.redirect("/user"),
        ]

    @rx.var(cache=False)
    def get_receiver(self) -> str:
        first_name = (
            self.dinner_signup_first_name
            if self.dinner_signup_first_name != ""
            else self.breakfast_signup_first_name
        )
        last_name = (
            self.dinner_signup_last_name
            if self.dinner_signup_last_name != ""
            else self.breakfast_signup_last_name
        )
        return generate_receiver_from_names(first_name, last_name)

    @rx.event
    def decrement_prepaid_dinners_quantity(self, session, nick_name: str):
        user: User = session.query(User).filter(User.nick_name == nick_name).scalar()
        user.prepaid_dinners_quantity -= 1
        user.is_synced = False

    @rx.event
    def order_dinner(self):
        self.has_sheet_data_finished_fetching = False
        now = get_madrid_datetime_now()
        order_id = self.item_uuid if self.is_stripe_session_paid else generate_uuid()
        dinner_price = (
            self.admin_data.get("dinner_price", 0)
            if not self.current_user.prepaid_dinners_quantity
            else 0
        )
        prepaid_dinner_suffix = (
            " (Prepaid)" if self.current_user.prepaid_dinners_quantity else ""
        )
        with rx.session() as session:
            session.add(
                Order(
                    order_id=order_id,
                    user_nick_name=self.current_user.nick_name,
                    time=now.strftime(DATETIME_FORMAT),
                    item=f"Dinner sign-up{prepaid_dinner_suffix}",
                    quantity=1,
                    price=dinner_price,
                    total=dinner_price,
                    receiver=self.get_receiver,
                    diet=self.dinner_signup_dietary_preference,
                    allergies=self.dinner_signup_allergies,
                    served="",
                    tax_category="Food and beverage non-alcoholic",
                    comment="",
                )
            )
            session.add(
                Meal(
                    meal_id=generate_uuid(),
                    order_id=order_id,
                    user_nick_name=self.current_user.nick_name,
                    receiver=self.get_receiver,
                    order_time=now,
                    meal_type="dinner",
                    diet=self.dinner_signup_dietary_preference,
                    allergies=self.dinner_signup_allergies,
                    volunteer=False,
                    served=False,
                )
            )
            if self.is_stripe_session_paid:
                session.add(
                    Payment(
                        payment_id=generate_uuid(),
                        order_id=self.item_uuid,
                        paid_time=now,
                        method="stripe-tablet",
                        checkout_staff="",
                    )
                )
            if self.current_user.prepaid_dinners_quantity:
                self.decrement_prepaid_dinners_quantity(
                    session, self.current_user.nick_name
                )
            session.commit()

        events = [rx.toast.info("Dinner sign-up registration successful!")]
        if not self.is_stripe_session_paid:
            # only redirect if the user hasn't paid with stripe
            self.current_order_request_id = ""
            events.append(rx.redirect("/user"))
        else:
            self.is_payment_status_written_to_db = True

        return events

    @rx.event
    def sign_guest_up_for_breakfast(self, is_guest_paying_now: bool):
        if self.order_request_id != self.current_order_request_id:
            return

        # Check for missing required fields
        missing_required_field_messages: list[str] = []

        def append_missing_field_message(message_suffix):
            missing_required_field_messages.append(f"MISSING FIELD - {message_suffix}")

        if self.breakfast_signup_first_name == "":
            append_missing_field_message("Please enter a first name.")

        if self.breakfast_signup_last_name == "":
            append_missing_field_message("Please enter a last name.")

        if self.breakfast_signup_item == "":
            append_missing_field_message("Please select a breakfast item to order")

        if len(missing_required_field_messages):
            return list(
                map(
                    lambda message: rx.toast.error(message),
                    missing_required_field_messages,
                )
            ) + [State.reset_order_request_id]

        # guests should not be able to sign up for multiple breakfasts, but they can sign up for multiple packed lunches

        if (
            not self.breakfast_signup_item.lower().startswith("packed lunch")
            and rx.session()
            .execute(
                Meal.select_todays_breakfast_meals().where(
                    Meal.receiver == self.get_receiver,
                    ~Meal.diet.ilike("packed lunch%"),
                )
            )
            .scalar()
        ):
            return [
                State.reset_order_request_id,
                rx.toast.error(
                    f"{self.get_receiver} is already signed up, "
                    "please provide different name if you want to sign up another person."
                ),
            ]

        if is_guest_paying_now:
            self.ordered_item = "breakfast"
            self.stripe_system_provider_handling_fee_amount = (
                get_system_provider_handling_fee_rounded_to_two_digits(
                    self.get_breakfast_price
                )
            )
            self.stripe_total = (
                self.get_breakfast_price
                + self.stripe_system_provider_handling_fee_amount
            )
            return State.generate_item_payment_qr

        return State.order_breakfast

    @rx.event
    def sign_guest_up_for_dinner(self, is_guest_paying_now: bool):
        if self.order_request_id != self.current_order_request_id:
            return
        if (
            rx.session()
            .execute(
                Meal.select_todays_dinner_meals().where(
                    Meal.receiver == self.get_receiver
                )
            )
            .scalar()
        ):
            return [
                State.reset_order_request_id,
                rx.toast.error(
                    f"{self.get_receiver} is already signed up, "
                    "please provide different name if you want to sign up another person."
                ),
            ]
        if is_guest_paying_now:
            self.ordered_item = "dinner"
            dinner_price = self.admin_data.get("dinner_price", 0)
            self.stripe_system_provider_handling_fee_amount = (
                get_system_provider_handling_fee_rounded_to_two_digits(dinner_price)
            )
            self.stripe_total = (
                dinner_price + self.stripe_system_provider_handling_fee_amount
            )
            return State.generate_item_payment_qr
        return State.order_dinner

    @rx.event
    def handle_add_another_press_for_late_dinner_signup(self):
        self.should_late_dinner_signup_form_reload = True

    @rx.event
    def order_dinner_late(self, form_data: dict):
        if (
            not len(form_data["nick_name"])
            or not form_data["full_name"]
            or not len(self.late_dinner_diet)
        ):
            return rx.toast.error("Please fill in all the details!")

        receiver = form_data["full_name"].upper().strip()

        if (
            rx.session()
            .exec(Meal.select_todays_dinner_meals().where(Meal.receiver == receiver))
            .first()
            is not None
        ):
            return [
                rx.set_value("full-name", form_data["full_name"]),
                rx.set_value("allergies", form_data["allergies"]),
                rx.toast.error(
                    f"A guest with this full name ({receiver}) is already signed up for dinner! Change the full name to sign this guest up. The full name is not case sensitive."
                ),
            ]

        user = self.get_user(form_data["nick_name"])
        with rx.session() as session:
            order_id = generate_uuid()
            now = get_madrid_datetime_now().strftime(DATETIME_FORMAT)
            price = (
                self.admin_data.get("dinner_price", 0)
                if not user.prepaid_dinners_quantity
                else 0
            )
            prepaid_dinner_suffix = (
                " (Prepaid)" if user.prepaid_dinners_quantity else ""
            )
            session.add(
                Order(
                    order_id=order_id,
                    user_nick_name=form_data["nick_name"],
                    time=now,
                    item=f"Dinner sign-up{prepaid_dinner_suffix}",
                    quantity=1,
                    price=price,
                    total=price,
                    receiver=receiver,
                    diet=form_data["diet"],
                    allergies=form_data["allergies"] if form_data["allergies"] else "",
                    served="",
                    tax_category="Food and beverage non-alcoholic",
                    comment="Late dinner signup",
                )
            )
            session.add(
                Meal(
                    meal_id=generate_uuid(),
                    order_id=order_id,
                    user_nick_name=form_data["nick_name"],
                    receiver=receiver,
                    order_time=datetime.strptime(now, DATETIME_FORMAT),
                    meal_type="dinner",
                    diet=form_data["diet"],
                    allergies=form_data["allergies"] if form_data["allergies"] else "",
                    volunteer=False,
                    served=False,
                )
            )
            if user.prepaid_dinners_quantity:
                self.decrement_prepaid_dinners_quantity(session, form_data["nick_name"])
            session.commit()

        events = [rx.toast(f"{form_data['full_name']} added successfully!")]
        if not self.should_late_dinner_signup_form_reload:
            events.append(rx.redirect("/admin/dinner"))
        self.should_late_dinner_signup_form_reload = False
        self.late_dinner_user_nick_name = None
        self.late_dinner_diet = ""
        return events

    @rx.var(cache=False)
    def get_breakfast_price(self) -> float:
        return self.admin_data.get(f"{self.breakfast_signup_item}_price", 0.0)

    @rx.event
    def order_breakfast(self):
        price = self.get_breakfast_price if not self.current_user.volunteer else 0.0
        now = get_madrid_datetime_now()
        order_id = order_id = (
            self.item_uuid if self.is_stripe_session_paid else generate_uuid()
        )
        with rx.session() as session:
            session.add(
                Order(
                    order_id=order_id,
                    user_nick_name=self.current_user.nick_name,
                    time=now.strftime(DATETIME_FORMAT),
                    item="Breakfast sign-up",
                    quantity=1,
                    price=price,
                    total=price,
                    receiver=self.get_receiver,
                    diet=self.breakfast_signup_item,
                    allergies=self.breakfast_signup_allergies,
                    served="",
                    tax_category="Food and beverage non-alcoholic",
                    comment="",
                )
            )
            session.add(
                Meal(
                    meal_id=generate_uuid(),
                    order_id=order_id,
                    user_nick_name=self.current_user.nick_name,
                    receiver=self.get_receiver,
                    order_time=now,
                    meal_type="breakfast",
                    diet=self.breakfast_signup_item,
                    allergies=self.breakfast_signup_allergies,
                    volunteer=False,
                    served=False,
                )
            )
            if self.is_stripe_session_paid:
                session.add(
                    Payment(
                        payment_id=generate_uuid(),
                        order_id=self.item_uuid,
                        paid_time=now,
                        method="stripe-tablet",
                        checkout_staff="",
                    )
                )
            session.commit()

        events = [rx.toast.info("Breakfast sign-up registration successful!")]
        if not self.is_stripe_session_paid:
            # only redirect if the user hasn't paid with stripe
            self.current_order_request_id = ""
            events.append(rx.redirect("/user"))
        else:
            self.is_payment_status_written_to_db = True

        return events

    @rx.event
    def submit_signup(self, form_data: dict):
        with rx.session() as session:
            session.add(
                User.model_validate(
                    {
                        **{key: str(form_data[key]) for key in form_data},
                        "is_synced": False,
                        "volunteer": False,
                        "away": False,
                    }
                )
            )
            session.commit()
        return State.redirect_to_homepage

    @rx.event
    def handle_checkout_choice(self, form_data: dict):
        self.stripe_system_provider_handling_fee_amount = (
            get_system_provider_handling_fee_rounded_to_two_digits(self.get_user_debt)
        )
        self.stripe_total = (
            self.get_user_debt + self.stripe_system_provider_handling_fee_amount
        )
        self.is_closing_account = form_data["is_closing_account"] == "Yes"

    @rx.event
    def close_guest_account(self):
        with rx.session() as session:
            if not self.is_closing_account:
                return

            user: User = (
                session.query(User)
                .filter(User.nick_name == self.current_user.nick_name)
                .scalar()
            )
            if not user:
                return rx.toast.error("Error checking guest out, please see reception.")
            user.has_active_tab = False
            user.is_synced = False
            session.add(
                Checkout(
                    checkout_id=generate_uuid(),
                    user=self.current_user.nick_name,
                    checkout_datetime=get_madrid_datetime_now(),
                    checkout_origin="stripe-tablet",
                    checkout_origin_payment_id=self.ob_payment_id,
                )
            )
            session.commit()

    @rx.event
    def pay_current_tab(self):
        now = get_madrid_datetime_now()
        with rx.session() as session:
            for order in self.current_user_orders:
                session.add(
                    Payment(
                        payment_id=generate_uuid(),
                        order_id=order.order_id,
                        paid_time=now,
                        method="stripe-tablet",
                        checkout_staff="",
                    )
                )
            session.commit()

        self.is_payment_status_written_to_db = True
        return [rx.toast.success("Tab paid successfully!"), State.reload_sheet_data]

    @rx.event
    def generate_line_items(self):
        line_items = []
        # sums up each item in the tab for a total quantity per item per price point to account for any price changes
        # eg. dinner x 3 @ €10 and dinner x 2 @ €12
        summarised_item_quantities = {}
        extra_line_item_total = 0
        last_item_total = 0

        for order in self.current_user_orders:
            name = order.item
            unit_amount = int(order.price * 100)
            if order.item == "Breakfast sign-up":
                name = get_full_breakfast_item(order.diet)
            if name not in summarised_item_quantities:
                summarised_item_quantities[name] = {}
            if unit_amount not in summarised_item_quantities[name]:
                summarised_item_quantities[name][unit_amount] = 0
            summarised_item_quantities[name][unit_amount] += int(order.quantity)

        for summarised_item in summarised_item_quantities:
            for summarised_item_price_point in summarised_item_quantities[
                summarised_item
            ]:
                summarised_item_quantity = summarised_item_quantities[summarised_item][
                    summarised_item_price_point
                ]
                # stripe cannot accept more than 100 line items in a checkout session.
                # if there are more than 100 items then it should display a total with a note to see reception for a full receipt
                # the number of receipt items is capped at 99 to give room for the system provider handling fee
                if len(line_items) == 98:
                    last_item_total = (
                        summarised_item_price_point * summarised_item_quantity
                    )
                if len(line_items) == 99:
                    extra_line_item_total += (
                        summarised_item_price_point * summarised_item_quantity
                    )
                    continue
                line_items.append(
                    generate_line_item(
                        summarised_item,
                        summarised_item_price_point,
                        summarised_item_quantity,
                    )
                )

        if extra_line_item_total:
            extra_line_item_total += last_item_total
            line_items[98] = generate_line_item(
                "Remaining item total - see reception for full receipt",
                extra_line_item_total,
                1,
            )

        return line_items

    # --- Payment Logic Handlers ---
    @rx.event(background=True)
    async def generate_item_payment_qr(
        self, item_name: str = "", unit_price: float = 0
    ):
        async with self:
            self.stripe_test_state = None
            self.show_stripe_timeout_message = False
            self.is_payment_status_written_to_db = False
            self.is_stripe_session_paid = False
            self.payment_qr_code = ""
            self.ob_payment_id = generate_uuid()

        individual_item_request: dict[str, str | float] = {}

        if item_name != "tab":
            async with self:
                self.item_uuid = generate_uuid()
            is_meal = self.ordered_item in ["breakfast", "dinner"]
            quantity = (
                self.temp_quantity if self.temp_quantity > 0 and not is_meal else 1.0
            )
            if self.ordered_item == "breakfast":
                item_name = get_full_breakfast_item(self.breakfast_signup_item)
                unit_price = self.get_breakfast_price
            if self.ordered_item == "dinner":
                item_name = "Dinner sign-up"
                unit_price = self.admin_data["dinner_price"]
            individual_item_request = {
                "order_id": self.item_uuid,
                "item": item_name,
                "quantity": quantity,
                "price": unit_price,
                "total": quantity * unit_price,
                "receiver": (self.get_receiver if is_meal else ""),
                "diet": (self.dinner_signup_dietary_preference if is_meal else ""),
                "allergies": (self.dinner_signup_allergies if is_meal else ""),
                "tax_category": (
                    "Food and beverage non-alcoholic"
                    if is_meal
                    else self.items[self.ordered_item].tax_category
                ),
                "comment": "",
            }

        line_items = (
            self.generate_line_items()
            if item_name == "tab"
            else [generate_line_item(item_name, int(unit_price * 100), int(quantity))]
        )
        line_items.append(
            generate_line_item(
                "System Provider Handling Fee",
                int(self.stripe_system_provider_handling_fee_amount * 100),
                1,
            )
        )

        if is_test_environment:
            datetime_requested = get_madrid_datetime_now().strftime(DATETIME_FORMAT)
            async with self:
                self.current_stripe_session_id = f"TEST-STRIPE-ID-{generate_uuid()}"
                self.payment_qr_code = "TEST_URL"
                self.test_line_items = line_items
        else:
            # 1. Create Stripe Checkout Session
            try:
                # This creates a payment page hosted by Stripe
                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode="payment",
                    metadata={"ob_payment_id": self.ob_payment_id},
                    # payment_intent_data allows staff to track the payment through the stripe dashboard using the payment id
                    payment_intent_data={
                        "metadata": {"ob_payment_id": self.ob_payment_id}
                    },
                    success_url=(
                        os.getenv("SUCCESS_URL")
                        if os.getenv("SUCCESS_URL")
                        else "https://example.com/success"
                    ),
                    cancel_url=(
                        os.getenv("CANCEL_URL")
                        if os.getenv("CANCEL_URL")
                        else "https://example.com/cancel"
                    ),
                    # the stripe session is set to expire after 30 minutes, this is the minimum expiry time for a checkout session, see https://docs.stripe.com/api/checkout/sessions/create
                    # this is to have the maximum frequency that the app can poll the stripe api without hitting the rate limit, see https://docs.stripe.com/rate-limits#api-read-request-allocations
                    expires_at=int(
                        (datetime.now(UTC) + timedelta(minutes=30)).timestamp()
                    ),
                )
                datetime_requested = datetime.fromtimestamp(
                    session.created, ZoneInfo("Europe/Madrid")
                ).strftime(DATETIME_FORMAT)
                async with self:
                    # 2. Generate QR Code pointing to that Stripe URL
                    self.current_stripe_session_id = session.id
                    self.payment_qr_code = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={quote(session.url)}"
            except Exception as e:
                print(f"Stripe Error: {e}", flush=True)
                async with self:
                    self.has_stripe_qr_generation_failed = True
                return

            if self.current_stripe_session_id == "":
                return
        with rx.session() as session:
            for order in (
                self.current_user_orders
                if item_name == "tab"
                else [individual_item_request]
            ):
                session.add(
                    Stripe_Checkout_Session(
                        payment_order_id=generate_uuid(),
                        datetime_requested=datetime_requested,
                        stripe_payment_id=self.current_stripe_session_id,
                        ob_payment_id=self.ob_payment_id,
                        order_id=(
                            order.order_id if item_name == "tab" else order["order_id"]
                        ),
                        user=self.current_user.nick_name,
                        system_provider_handling_fee_amount=self.stripe_system_provider_handling_fee_amount,
                        item=order.item if item_name == "tab" else order["item"],
                        quantity=(
                            order.quantity if item_name == "tab" else order["quantity"]
                        ),
                        price=order.price if item_name == "tab" else order["price"],
                        total=order.total if item_name == "tab" else order["total"],
                        receiver=(
                            order.receiver if item_name == "tab" else order["receiver"]
                        ),
                        diet=order.diet if item_name == "tab" else order["diet"],
                        allergies=(
                            order.allergies
                            if item_name == "tab"
                            else order["allergies"]
                        ),
                        tax_category=(
                            order.tax_category
                            if item_name == "tab"
                            else order["tax_category"]
                        ),
                        comment=(
                            order.comment if item_name == "tab" else order["comment"]
                        ),
                    )
                )
            session.commit()

        return State.check_stripe_payment_status

    @rx.event(background=True)
    async def check_stripe_payment_status(self):
        """Periodically checks if payment was successful"""
        stripe_error_message = ""
        # read requests are limited to 500 requests per transaction, see https://docs.stripe.com/rate-limits#api-read-request-allocations
        stripe_api_get_rate_limit_per_transaction = 500
        request_count = 0

        while True:
            if (
                self.current_stripe_session_id == ""
                or self.is_stripe_session_paid
                or not self.is_client_still_connected()
            ):
                return

            async with self:
                self.update_last_user_activity_datetime()

            if is_test_environment:
                if not self.stripe_test_state:
                    await asyncio.sleep(1)
                    continue
            else:
                request_count += 1
                result = False

                try:
                    check_internet_connection()
                    session = stripe.checkout.Session.retrieve(
                        self.current_stripe_session_id
                    )
                    if session.status == "expired":
                        async with self:
                            self.show_stripe_timeout_message = True
                        return
                    result = session.payment_status == "paid"
                    stripe_error_message = ""
                    async with self:
                        self.show_stripe_connection_failure_message = False
                except Exception as e:
                    if stripe_error_message != str(e):
                        stripe_error_message = str(e)
                        print(
                            f"Stripe Error: {stripe_error_message} - {get_madrid_datetime_now()}",
                            flush=True,
                        )
                    async with self:
                        self.show_stripe_connection_failure_message = True

                if not result:
                    if request_count < stripe_api_get_rate_limit_per_transaction:
                        # 500 requests spread over 30 minutes is 3.607 secs/request, rounded up to 3.7
                        await asyncio.sleep(3.7)
                        continue
                    async with self:
                        self.show_stripe_timeout_message = True
                    return

            async with self:
                self.is_stripe_session_paid = True
            if self.ordered_item != "":
                if self.ordered_item == "dinner":
                    return State.order_dinner
                if self.ordered_item == "breakfast":
                    return State.order_breakfast
                return State.order_item
            # if no item has been ordered then it must be the entire tab.
            return [State.pay_current_tab, State.close_guest_account]

    def open_item_dialog(self, item_name: str):
        self.update_last_user_activity_datetime()
        self.temp_quantity = 1
        self.ordered_item = item_name

    @rx.event(background=True)
    async def show_stripe_item_payment_dialog(self, item_name: str, amount: float):
        if self.current_order_request_id != self.order_request_id:
            return
        async with self:
            self.stripe_system_provider_handling_fee_amount = (
                get_system_provider_handling_fee_rounded_to_two_digits(amount)
            )
            self.stripe_total = amount + self.stripe_system_provider_handling_fee_amount
            self.is_stripe_dialog_active = True
        async with self:
            self.update_last_user_activity_datetime()
        yield State.generate_item_payment_qr(item_name, amount)

    @rx.event
    def close_item_dialog(self):
        self.update_last_user_activity_datetime()
        temp_ordered_item = self.ordered_item
        temp_is_stripe_session_paid = self.is_stripe_session_paid
        self.payment_qr_code = ""

        if self.current_stripe_session_id != "":
            yield State.expire_stripe_session

        self.is_stripe_session_paid = False
        self.is_payment_status_written_to_db = False
        self.is_stripe_dialog_active = False
        self.ordered_item = ""
        self.is_closing_account = None
        self.show_stripe_connection_failure_message = False
        self.has_stripe_qr_generation_failed = False
        self.current_order_request_id = ""
        yield State.reset_order_request_id
        if (
            temp_ordered_item == "dinner" or temp_ordered_item == "breakfast"
        ) and temp_is_stripe_session_paid:
            return rx.redirect("/user")

    # -----------------------------------

    @rx.var
    def current_user_orders_in_reverse_chronological_order(self) -> List[Order]:
        current_user_orders_copy = self.current_user_orders.copy()
        current_user_orders_copy.reverse()
        return current_user_orders_copy

    @rx.event
    def update_current_user_orders(self) -> List[Order]:
        if not self.current_user:
            return []

        orders = (
            rx.session()
            .query(Order)
            .filter(
                Order.user_nick_name == self.current_user.nick_name,
                ~exists().where(Payment.order_id == Order.order_id),
            )
            .all()
        )

        for order in orders:
            order = order.model_dump()
            try:
                order.time = datetime.fromisoformat(order.time).strftime(
                    "%d/%m/%Y, %H:%M:%S"
                )
            except BaseException:
                pass

        orders.sort(
            key=lambda order: datetime.strptime(order.time, "%d/%m/%Y %H:%M:%S")
        )
        self.current_user_orders = orders

    @rx.var
    def no_user(self) -> bool:
        return self.current_user is None

    @rx.var
    def invalid_new_user_name(self) -> bool:
        return (
            self.new_nick_name in [x.nick_name for x in self.users]
            and self.new_nick_name != ""
        )

    @rx.var
    def invalid_custom_item_price(self) -> bool:
        try:
            float_val = float(self.custom_item_price)
            if len(str(float_val).split(".")[-1]) <= 2:
                return False
            return True
        except ValueError:
            return True

    @rx.var(cache=False)
    def dinner_signup_available(self) -> int:
        try:
            deadline = datetime.strptime(
                self.admin_data.get("dinner_signup_deadline", "22:59"), "%H:%M"
            )
        except BaseException:
            deadline = datetime.strptime("22:59", "%H:%M")
        now = get_madrid_datetime_now()
        deadline_minutes = deadline.hour * 60 + deadline.minute
        now_minutes = now.hour * 60 + now.minute
        return now_minutes < deadline_minutes

    @rx.var(cache=False)
    def breakfast_signup_available(self) -> bool:
        try:
            deadline = datetime.strptime(
                self.admin_data.get("breakfast_signup_deadline", "22:59"), "%H:%M"
            )
        except BaseException:
            deadline = datetime.strptime("22:59", "%H:%M")
        now = get_madrid_datetime_now()
        deadline_minutes = deadline.hour * 60 + deadline.minute
        now_minutes = now.hour * 60 + now.minute
        return now_minutes < deadline_minutes

    @rx.var
    def get_user_debt(self) -> float:
        return sum([order.total for order in self.current_user_orders])

    @rx.var
    def are_user_buttons_disabled(self) -> bool:
        return any(
            (
                self.is_stripe_dialog_active,
                self.is_logging_user_in,
                not self.has_sheet_data_finished_fetching,
            )
        )
