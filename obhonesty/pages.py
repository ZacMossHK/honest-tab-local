import reflex as rx
import os
from obhonesty.aux import two_decimal_points
from obhonesty.constants import *
from obhonesty.state import State
from obhonesty.elements import (
    admin_refresh_top_bar,
    show_row,
    show_signup,
    user_button,
    user_button_dialog,
    logout_button,
    item_button,
    stripe_payment_dialog,
    admin_last_update_message,
)

is_test_environment = True if os.getenv("TEST") else False


def index() -> rx.Component:
    return rx.container(
        rx.center(
            rx.vstack(
                rx.hstack(
                    rx.text("Welcome to the", size="3"),
                    justify="center",
                    width="100%",
                ),
                rx.hstack(
                    rx.heading(
                        "Olive Branch honest self-service",
                        size=default_heading_size,
                        **{"data-testid": "title"},
                    ),
                    justify="center",
                    width="100%",
                ),
                rx.cond(
                    State.has_sheet_data_finished_fetching,
                    rx.hstack(
                        rx.text("New here?", size="3"),
                        rx.button(
                            rx.icon("user-plus"),
                            rx.text(
                                "Sign up for self-service",
                                size=default_button_text_size,
                                **{"data-testid": "sign-up-user-button"},
                            ),
                            color_scheme="green",
                            on_click=rx.redirect("/signup"),
                            size="3",
                        ),
                        align="center",
                        justify="center",
                        width="100%",
                    ),
                    rx.text("Loading..."),
                ),
                rx.cond(
                    State.has_sheet_data_finished_fetching,
                    rx.scroll_area(
                        rx.flex(
                            rx.foreach(State.users, user_button_dialog),
                            padding="8px",
                            spacing="5",
                            style={"width": "max"},
                            wrap="wrap",
                        ),
                        type="always",
                        scrollbars="vertical",
                        style={"height": "80vh"},
                    ),
                ),
            ),
            align="center",
        )
    )


def error_page() -> rx.Component:
    return rx.vstack(
        rx.text(
            "An error occurred, please press the button below.", size=default_text_size
        ),
        rx.button(
            rx.icon("door-open"),
            "Return",
            on_click=State.redirect_to_homepage,
            size=default_button_size,
        ),
    )


def user_page() -> rx.Component:
    return rx.container(
        rx.center(
            rx.cond(
                State.no_user,
                error_page(),
                rx.vstack(
                    rx.heading(
                        f"Hello {State.current_user.nick_name}",
                        size=default_heading_size,
                        **{"data-testid": f"user-page-heading"},
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon("list"),
                            rx.text("View orders", size=default_button_text_size),
                            on_click=rx.redirect("/info"),
                            color_scheme="green",
                            size=default_button_size,
                            disabled=State.are_user_buttons_disabled,
                            **{"data-testid": "view-orders-button"},
                        ),
                        logout_button(),
                        rx.text(
                            "(please log out when you're done)", size=default_text_size
                        ),
                        align="center",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon("egg-fried"),
                            rx.text(
                                "Sign up for breakfast / packed lunch",
                                size=default_button_text_size,
                            ),
                            on_click=rx.redirect("/breakfast"),
                            size=default_button_size,
                            disabled=(
                                ~State.breakfast_signup_available
                                & (not is_test_environment)
                            )
                            | State.are_user_buttons_disabled,
                            **{"data-testid": "breakfast-signup-button"},
                        ),
                        rx.text(
                            f"(last sign-up at {State.admin_data['breakfast_signup_deadline']})",
                            size=default_text_size,
                        ),
                        align="center",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon("utensils"),
                            rx.text(
                                "Sign up for dinner",
                                size=default_button_text_size,
                            ),
                            on_click=rx.redirect("/dinner"),
                            size=default_button_size,
                            disabled=(
                                ~State.dinner_signup_available
                                & (not is_test_environment)
                            )
                            | State.are_user_buttons_disabled,
                            **{"data-testid": "dinner-signup-button"},
                        ),
                        rx.text(
                            f"(last sign-up at {State.admin_data['dinner_signup_deadline']}, "
                            f"for late sign-ups, please ask the kitchen staff)",
                            size=default_text_size,
                        ),
                        align="center",
                    ),
                    rx.cond(
                        State.are_payments_enabled,
                        rx.hstack(
                            rx.button(
                                rx.icon("euro"),
                                rx.text("Pay tab", size=default_button_text_size),
                                on_click=rx.redirect("/info"),
                                size=default_button_size,
                                color_scheme="yellow",
                                disabled=State.are_user_buttons_disabled,
                                **{"data-testid": "pay-tab-button"},
                            ),
                            rx.text(
                                f"Pay your tab securely via Stripe.",
                                size=default_text_size,
                            ),
                            align="center",
                        ),
                    ),
                    rx.text("Register an item", weight="bold", size=default_text_size),
                    rx.scroll_area(
                        rx.flex(
                            rx.foreach(State.items.values(), item_button),
                            padding="8px",
                            spacing="4",
                            style={"width": "max"},
                            wrap="wrap",
                        ),
                        type="always",
                        scrollbars="vertical",
                        style={"height": "60vh"},
                    ),
                    rx.hstack(
                        rx.text(
                            "Didn't find the item? No problem, just",
                            size=default_text_size,
                        ),
                        rx.button(
                            rx.icon("circle-plus"),
                            rx.text("Register manually", size=default_button_text_size),
                            color_scheme="sky",
                            on_click=rx.redirect("/custom_item"),
                            size=default_button_size,
                            disabled=State.are_user_buttons_disabled,
                            **{"data-testid": "custom-item-button"},
                        ),
                        align="center",
                    ),
                ),
            )
        )
    )


def custom_item_page() -> rx.Component:
    return rx.container(
        rx.center(
            rx.vstack(
                rx.heading("Register custom item", size=default_heading_size),
                rx.form(
                    rx.vstack(
                        rx.text("Name"),
                        rx.input(
                            placeholder="What did you get?",
                            name="custom_item_name",
                            **{"data-testid": "custom-item-name-input"},
                        ),
                        rx.text("Price"),
                        rx.form.field(
                            rx.form.control(
                                rx.input(
                                    placeholder="E.g. 2.50 for (2.50€)",
                                    name="custom_item_price",
                                    on_change=State.set_custom_item_price,
                                    **{"data-testid": "custom-item-price-input"},
                                ),
                                as_child=True,
                            ),
                            rx.form.message(
                                "Please enter a valid price",
                                match="valueMissing",
                                force_match=State.invalid_custom_item_price,
                                color=ERROR_MESSAGE_COLOUR,
                            ),
                        ),
                        rx.text("Category"),
                        rx.select(
                            [str(x) for x in TaxCategory],
                            default_value=TaxCategory.NON_ALCOHOLIC,
                            name="tax_category",
                            required=True,
                        ),
                        rx.text("Comment"),
                        rx.input(
                            placeholder="optional", name="custom_item_description"
                        ),
                        rx.button(
                            rx.text("Register", size=default_button_text_size),
                            type="submit",
                            size=default_button_size,
                            **{"data-testid": "custom-item-register-button"},
                        ),
                    ),
                    on_submit=State.order_custom_item,
                ),
                rx.button(
                    rx.text("Cancel", size=default_button_text_size),
                    on_click=rx.redirect("/user"),
                    size=default_button_size,
                ),
            )
        )
    )


def user_signup_page() -> rx.Component:
    return rx.container(
        rx.center(
            rx.vstack(
                rx.heading("Welcome to the Olive Branch", size=default_heading_size),
                rx.text("Please fill in your details to get started with self-service"),
                rx.form(
                    rx.vstack(
                        rx.text("User name", weight="medium"),
                        rx.form.field(
                            rx.form.control(
                                rx.input(
                                    placeholder="E.g. 'Bob' (required)",
                                    on_change=State.check_new_nick_name,
                                    name="nick_name",
                                    required=True,
                                    width="200%",
                                    **{"data-testid": "user-name-input"},
                                ),
                                as_child=True,
                            ),
                            rx.form.message(
                                State.new_user_name_error_message,
                                match="valueMissing",
                                force_match=State.is_new_nick_name_invalid,
                                color=ERROR_MESSAGE_COLOUR,
                                **{"data-testid": "user-name-error-message"},
                            ),
                        ),
                        rx.text("First name", weight="medium"),
                        rx.input(
                            placeholder="E.g. 'Robert' (required)",
                            name="first_name",
                            required=True,
                            width="100%",
                            **{"data-testid": "first-name-input"},
                        ),
                        rx.text("Last name", weight="medium"),
                        rx.input(
                            placeholder="E.g. 'Robertson' (required)",
                            name="last_name",
                            required=True,
                            width="100%",
                            **{"data-testid": "last-name-input"},
                        ),
                        rx.text("Phone number", weight="medium"),
                        rx.input(
                            placeholder="E.g. '+45 12345666' (required)",
                            name="phone_number",
                            required=True,
                            width="100%",
                            **{"data-testid": "phone-number-input"},
                        ),
                        rx.text("Email", weight="medium"),
                        rx.input(
                            placeholder="E.g. 'olivebranchelchorro@gmail.com' (required)",
                            name="email",
                            required=True,
                            type="email",
                            width="100%",
                            **{"data-testid": "email-input"},
                        ),
                        rx.text("Dietary preferences", weight="medium"),
                        rx.select(
                            [str(x) for x in Diet],
                            placeholder="Select a dietary preference",
                            name="diet",
                            required=True,
                            **{"data-testid": "diet-select"},
                        ),
                        rx.text("Allergies", weight="medium"),
                        rx.input(
                            placeholder="e.g. Peanuts, Shellfish (Anaphylaxis risk)",
                            name="allergies",
                            width="70%",
                            border_color="tomato",
                            **{"data-testid": ["allergies-input"]},
                        ),
                        rx.text(
                            "Are you currently staying at the Olive Branch?",
                            weight="medium",
                        ),
                        rx.radio_group.root(
                            rx.foreach(
                                ["Yes", "No"],
                                lambda x: rx.radio_group.item(
                                    x,
                                    value=x,
                                    **{"data-testid": f"radio-input-{x.lower()}"},
                                ),
                            ),
                            required=True,
                            name="is_current_guest",
                            default_value="Yes",
                            direction="row",
                        ),
                        rx.text("If this changes please notify reception."),
                        rx.spacer(),
                        rx.button(
                            rx.text("Submit", size=default_button_text_size),
                            type="submit",
                            size=default_button_size,
                            disabled=State.is_new_nick_name_invalid,
                            **{"data-testid": "user-submit-button"},
                        ),
                    ),
                    on_submit=State.submit_signup,
                    reset_on_submit=True,
                ),
                rx.button(
                    rx.text("Cancel", size=default_button_text_size),
                    on_click=State.redirect_to_homepage,
                    size=default_button_size,
                    color_scheme="red",
                ),
            ),
        ),
    )


def dinner_signup_page() -> rx.Component:
    prepaid_dinners_plural = rx.cond(
        State.current_user.prepaid_dinners_quantity > 1, "s", ""
    )
    return rx.container(
        rx.center(
            rx.vstack(
                rx.vstack(
                    rx.heading("Sign up for dinner", size=default_heading_size),
                    rx.text(
                        f"Note: you are signing up for todays dinner. "
                        f"Sign up again tomorrow for tomorrows dinner. "
                        f"Price per person is {State.admin_data['dinner_price']}€. "
                        f"If you are signing up yourself, just write your own full name. "
                        f"You can also sign up someone else on your tab, "
                        f"in that case write the full name of the guest "
                        f"whom you are signing up."
                    ),
                    rx.text("First name of dinner guest", weight="bold"),
                    rx.input(
                        placeholder="First name of dinner guest",
                        name="first_name",
                        default_value=State.current_user.first_name,
                        required=True,
                        on_change=State.set_dinner_signup_first_name,
                        **{"data-testid": f"dinner-signup-first-name"},
                    ),
                    rx.text("Last name of dinner guest", weight="bold"),
                    rx.input(
                        placeholder="Last name of dinner guest",
                        name="last_name",
                        default_value=State.current_user.last_name,
                        required=True,
                        on_change=State.set_dinner_signup_last_name,
                        **{"data-testid": f"dinner-signup-last-name"},
                    ),
                    rx.text("Dietary preferences", weight="bold"),
                    rx.select(
                        [str(x) for x in Diet],
                        default_value=State.current_user.diet,
                        name="diet",
                        on_change=State.set_dinner_dietary_preference,
                    ),
                    rx.text("Allergies", weight="bold"),
                    rx.input(
                        default_value=State.current_user.allergies,
                        name="allergies",
                        on_change=State.set_dinner_allergies,
                        **{"data-testid": f"dinner-signup-allergies"},
                    ),
                    rx.divider(),
                    rx.cond(
                        State.current_user.prepaid_dinners_quantity > 0,
                        rx.text.strong(
                            f"You currently have {State.current_user.prepaid_dinners_quantity} prepaid dinner{prepaid_dinners_plural} remaining.",
                            **{"data-testid": "prepaid-dinners-message"},
                        ),
                    ),
                    rx.button(
                        rx.text("Register", size=default_button_text_size),
                        size=default_button_size,
                        on_click=[
                            State.set_order_request_id,
                            lambda: State.sign_guest_up_for_dinner(False),
                        ],
                        loading=State.is_order_request_loading,
                        **{"data-testid": f"dinner-signup-register"},
                    ),
                    rx.cond(
                        State.are_payments_enabled,
                        rx.button(
                            rx.icon("credit-card"),
                            rx.text("Pay Now", size=default_button_text_size),
                            color_scheme="green",
                            size=default_button_size,
                            type="button",
                            loading=State.is_order_request_loading,
                            on_click=[
                                State.set_order_request_id,
                                lambda: State.sign_guest_up_for_dinner(True),
                            ],
                            **{"data-testid": f"dinner-signup-pay-now"},
                        ),
                    ),
                    rx.dialog.root(
                        stripe_payment_dialog(
                            "dinner", State.admin_data["dinner_price"]
                        ),
                        open=State.ordered_item == "dinner",
                    ),
                    rx.button(
                        rx.text("Cancel", size=default_button_text_size),
                        on_click=rx.redirect("/user"),
                        size=default_button_size,
                        color_scheme="red",
                    ),
                ),
            )
        ),
        on_mount=State.set_dinner_signup_default_values,
    )


def late_dinner_signup_page() -> rx.Component:
    is_late_dinner_user_selected = State.late_dinner_user_nick_name != None
    user_selection_button_colour_scheme = "green"

    return rx.container(
        rx.center(
            rx.vstack(
                rx.form(
                    rx.vstack(
                        rx.heading("Late dinner signup", size=default_heading_size),
                        rx.hstack(
                            rx.cond(
                                is_late_dinner_user_selected,
                                rx.hstack(
                                    rx.text("User to pay:", size="5"),
                                    rx.text(
                                        State.late_dinner_user_nick_name,
                                        weight="bold",
                                        size="5",
                                        **{"data-testid": "late-signup-user-to-pay"},
                                    ),
                                ),
                            ),
                            rx.dialog.root(
                                rx.dialog.trigger(
                                    rx.button(
                                        rx.cond(
                                            is_late_dinner_user_selected,
                                            "Select another user",
                                            "Select a user to pay for this dinner sign-up",
                                        ),
                                        color_scheme=user_selection_button_colour_scheme,
                                        size=default_button_size,
                                        **{
                                            "data-testid": "late-signup-user-select-button"
                                        },
                                    )
                                ),
                                rx.dialog.content(
                                    rx.vstack(
                                        rx.dialog.title(
                                            "Select a user to pay for this dinner sign-up"
                                        ),
                                        rx.scroll_area(
                                            rx.flex(
                                                rx.foreach(
                                                    State.users,
                                                    lambda user: rx.dialog.close(
                                                        user_button(
                                                            user.nick_name,
                                                            on_click=[
                                                                lambda: State.set_late_dinner_user_nick_name(
                                                                    user.nick_name
                                                                ),
                                                                rx.set_value(
                                                                    "full-name",
                                                                    f"{user.first_name} {user.last_name}",
                                                                ),
                                                                rx.set_value(
                                                                    "allergies",
                                                                    user.allergies,
                                                                ),
                                                            ],
                                                            **{
                                                                "data-testid": f"late-signup-user-select-button-{user.nick_name}"
                                                            },
                                                        )
                                                    ),
                                                ),
                                                padding="8px",
                                                spacing="4",
                                                style={"width": "max"},
                                                wrap="wrap",
                                            ),
                                            type="always",
                                            scrollbars="vertical",
                                            style={"height": "80vh"},
                                        ),
                                        rx.dialog.close(
                                            rx.button(
                                                "Back",
                                                size=default_button_size,
                                                color_scheme="red",
                                            )
                                        ),
                                    ),
                                ),
                            ),
                            align="center",
                        ),
                        rx.input(
                            type="hidden",
                            display="none",
                            value=State.late_dinner_user_nick_name,
                            name="nick_name",
                        ),
                        rx.vstack(
                            rx.text("Full name of dinner guest", weight="bold"),
                            rx.input(
                                placeholder="Full name",
                                name="full_name",
                                required=True,
                                **{"data-testid": "late-signup-full-name-input"},
                                id="full-name",
                                disabled=~is_late_dinner_user_selected,
                            ),
                            rx.text("Dietary preferences", weight="bold"),
                            rx.select.root(
                                rx.select.trigger(
                                    placeholder="Select a dietary preference",
                                    **{"data-testid": "late-signup-item-select"},
                                ),
                                rx.select.content(
                                    rx.foreach(
                                        [str(x) for x in Diet],
                                        lambda item: rx.select.item(
                                            item,
                                            value=item,
                                            **{
                                                "data-testid": "late-signup-item-option"
                                            },
                                        ),
                                    )
                                ),
                                name="diet",
                                value=State.late_dinner_diet,
                                required=True,
                                disabled=~is_late_dinner_user_selected,
                                on_change=State.set_late_dinner_diet,
                            ),
                            rx.text(
                                "Allergies",
                                weight="bold",
                            ),
                            rx.input(
                                name="allergies",
                                id="allergies",
                                disabled=~is_late_dinner_user_selected,
                                **{"data-testid": "late-signup-allergies"},
                            ),
                        ),
                        rx.hstack(
                            rx.button(
                                rx.text("Register", size=default_button_text_size),
                                type="submit",
                                size=default_button_size,
                                disabled=~is_late_dinner_user_selected
                                | State.late_dinner_diet
                                == "",
                                **{"data-testid": "late-signup-register-button"},
                            ),
                            rx.button(
                                rx.text(
                                    "Register and add another",
                                    size=default_button_text_size,
                                    **{
                                        "data-testid": "late-signup-register-and-add-another-button"
                                    },
                                ),
                                type="submit",
                                size=default_button_size,
                                disabled=~is_late_dinner_user_selected
                                | State.late_dinner_diet
                                == "",
                                on_click=State.handle_add_another_press_for_late_dinner_signup,
                            ),
                        ),
                    ),
                    on_submit=State.order_dinner_late,
                    reset_on_submit=True,
                ),
                rx.button(
                    rx.text("Cancel", size=default_button_text_size),
                    on_click=[
                        State.reset_late_dinner_user_nick_name,
                        rx.redirect("/admin/dinner"),
                    ],
                    size=default_button_size,
                    **{"data-testid": "late-signup-cancel-button"},
                ),
            )
        )
    )


def breakfast_signup_page() -> rx.Component:
    return rx.container(
        rx.center(
            rx.vstack(
                rx.heading("Sign up for breakfast", size=default_heading_size),
                rx.text(
                    "Note: you are signing up for todays breakfast. "
                    "Sign up again tomorrow for tomorrows breakfast."
                ),
                rx.text("* = Required field"),
                rx.spacer(),
                rx.text("First name of breakfast guest *"),
                rx.input(
                    placeholder="First name of breakfast guest",
                    default_value=State.current_user.first_name,
                    name="first_name",
                    on_change=State.set_breakfast_signup_first_name,
                    **{"data-testid": "breakfast-signup-first-name"},
                ),
                rx.text("Last name of breakfast guest *"),
                rx.input(
                    placeholder="Last name of breakfast guest",
                    default_value=State.current_user.last_name,
                    name="last_name",
                    on_change=State.set_breakfast_signup_last_name,
                    **{"data-testid": "breakfast-signup-last-name"},
                ),
                rx.text("Breakfast item *"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Select a breakfast item",
                        **{"data-testid": "breakfast-signup-item-select"},
                    ),
                    rx.select.content(
                        rx.foreach(
                            [str(x) for x in BreakfastMenuItem],
                            lambda item: rx.select.item(
                                f"{item} ({State.admin_data[item + '_price']}€)",
                                value=item,
                                **{"data-testid": "breakfast-signup-item-option"},
                            ),
                        )
                    ),
                    name="menu_item",
                    on_change=State.set_breakfast_signup_item,
                ),
                rx.text("Allergies"),
                rx.input(
                    name="allergies",
                    default_value=State.current_user.allergies,
                    on_change=State.set_breakfast_signup_allergies,
                    **{"data-testid": "breakfast-signup-allergies"},
                ),
                rx.button(
                    rx.text("Register", size=default_button_text_size),
                    size=default_button_size,
                    loading=State.is_order_request_loading,
                    on_click=[
                        State.set_order_request_id,
                        lambda: State.sign_guest_up_for_breakfast(False),
                    ],
                    **{"data-testid": "breakfast-signup-register"},
                ),
                rx.cond(
                    State.are_payments_enabled,
                    rx.button(
                        rx.icon("credit-card"),
                        rx.text("Pay Now", size=default_button_text_size),
                        color_scheme="green",
                        size=default_button_size,
                        type="button",
                        loading=State.is_order_request_loading,
                        on_click=[
                            State.set_order_request_id,
                            lambda: State.sign_guest_up_for_breakfast(True),
                        ],
                        **{"data-testid": "breakfast-pay-now"},
                    ),
                ),
                rx.dialog.root(
                    stripe_payment_dialog("breakfast", State.get_breakfast_price),
                    open=State.ordered_item == "breakfast",
                ),
                rx.button(
                    rx.text("Cancel", size=default_button_text_size),
                    on_click=rx.redirect("/user"),
                    size=default_button_size,
                ),
            )
        ),
        on_mount=State.set_breakfast_signup_default_values,
    )


def user_info_page() -> rx.Component:
    is_user_debt_0 = State.get_user_debt == 0
    return rx.container(
        rx.center(
            rx.vstack(
                rx.heading(
                    f"Hello {State.current_user.nick_name}", size=default_heading_size
                ),
                rx.button(
                    rx.text(f"Back to orders and items", size=default_button_text_size),
                    on_click=rx.redirect("/user"),
                    color_scheme="red",
                    size=default_button_size,
                ),
                rx.text(
                    "Note: new orders may take a moment to show. "
                    "If you made a registration by mistake, please talk to the reception "
                    "and they will help correcting it.",
                    size=default_text_size,
                ),
                rx.text(
                    f"Total amount due: €{two_decimal_points(State.get_user_debt)}",
                    size=default_text_size,
                    weight="bold",
                    **{"data-testid": "total-amount-due"},
                ),
                rx.cond(
                    State.are_payments_enabled,
                    rx.hstack(
                        rx.dialog.root(
                            rx.dialog.trigger(
                                rx.button(
                                    rx.icon("euro"),
                                    rx.text(
                                        "Pay tab",
                                        size=default_button_text_size,
                                        weight="bold",
                                    ),
                                    size=default_button_size,
                                    color_scheme="yellow",
                                    disabled=is_user_debt_0,
                                    **{"data-testid": "pay-tab-button"},
                                )
                            ),
                            rx.cond(
                                State.is_closing_account == None,
                                rx.dialog.content(
                                    rx.form(
                                        rx.vstack(
                                            rx.text(
                                                rx.cond(
                                                    State.current_user.is_current_guest
                                                    == True,
                                                    "Are you leaving the Olive Branch?",
                                                    "Are you closing your account?",
                                                ),
                                                weight="medium",
                                            ),
                                            rx.radio_group.root(
                                                rx.foreach(
                                                    ["Yes", "No"],
                                                    lambda x: rx.radio_group.item(
                                                        x,
                                                        value=x,
                                                        **{
                                                            "data-testid": f"radio-input-{x.lower()}"
                                                        },
                                                    ),
                                                ),
                                                required=True,
                                                name="is_closing_account",
                                                default_value="Yes",
                                                direction="row",
                                            ),
                                            rx.hstack(
                                                rx.button(
                                                    rx.text(
                                                        "Submit",
                                                        size=default_button_text_size,
                                                    ),
                                                    type="submit",
                                                    size=default_button_size,
                                                    **{"data-testid": "submit-button"},
                                                ),
                                                rx.dialog.close(
                                                    rx.button(
                                                        "Close",
                                                        size=default_button_size,
                                                    )
                                                ),
                                            ),
                                        ),
                                        on_submit=[
                                            State.handle_checkout_choice,
                                            lambda: State.generate_item_payment_qr(
                                                "tab", State.get_user_debt
                                            ),
                                        ],
                                    )
                                ),
                                stripe_payment_dialog("tab", State.get_user_debt),
                            ),
                        ),
                        rx.text(
                            f"Pay your tab securely via Stripe. Please review your registrations below before paying.",
                            size=default_text_size,
                            opacity=rx.cond(is_user_debt_0, 0.3, 1),
                        ),
                        align="center",
                    ),
                ),
                rx.cond(
                    is_user_debt_0,
                    rx.text(
                        "You have no orders to pay for! Please see reception if you wish to check out.",
                        size=default_text_size,
                    ),
                ),
                rx.text("Orders:", size=default_text_size, weight="bold"),
                rx.scroll_area(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Time"),
                                rx.table.column_header_cell("Item"),
                                rx.table.column_header_cell("Quantity", align="right"),
                                rx.table.column_header_cell(
                                    "Unit Price", align="right"
                                ),
                                rx.table.column_header_cell("Total", align="right"),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                State.current_user_orders_in_reverse_chronological_order,
                                show_row,
                            )
                        ),
                    ),
                    scrollbars="vertical",
                    style={"height": "70vh"},
                ),
            )
        )
    )


def admin() -> rx.Component:
    return rx.container(
        rx.center(
            rx.vstack(
                rx.heading(f"Admin", size=default_heading_size),
                rx.button(
                    rx.text("Breakfast", size=default_button_text_size),
                    on_click=rx.redirect("/admin/breakfast"),
                    size=default_button_size,
                ),
                rx.button(
                    rx.text("Dinner", size=default_button_text_size),
                    on_click=rx.redirect("/admin/dinner"),
                    size=default_button_size,
                ),
            )
        )
    )


def admin_dinner() -> rx.Component:
    return rx.container(
        rx.center(
            rx.vstack(
                rx.heading("Dinner", size=default_heading_size),
                rx.vstack(
                    rx.hstack(
                        admin_refresh_top_bar(),
                        rx.button(
                            rx.text("Late sign-up", size=default_button_text_size),
                            on_click=State.redirect_to_later_dinner_signup,
                            size=default_button_size,
                            disabled=State.is_loading_admin_meal_table,
                            **{"data-testid": "late-signup-button"},
                        ),
                        spacing="2",
                    ),
                    admin_last_update_message(),
                ),
                # Make the two columns share the available space evenly
                rx.cond(
                    ~State.is_loading_admin_meal_table,
                    rx.hstack(
                        rx.vstack(
                            rx.text.strong(
                                f"Total eating dinner: {State.dinner_count}"
                            ),
                            rx.text.strong(
                                f"Total served: {State.dinner_count_served}",
                                **{"data-testid": "total-served"},
                            ),
                            rx.text(f"Meat: {State.dinner_count_meat}"),
                            rx.text(f"Vegetarian: {State.dinner_count_vegetarian}"),
                            rx.text(f"Vegan: {State.dinner_count_vegan}"),
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text.strong(
                                f"Guests eating dinner: {State.dinner_count_guests}"
                            ),
                            rx.text.strong(
                                f"Total served: {State.dinner_count_guests_served}",
                                **{"data-testid": "total-guests-served"},
                            ),
                            rx.text(f"Meat: {State.dinner_count_guests_meat}"),
                            rx.text(
                                f"Vegetarian: {State.dinner_count_guests_vegetarian}"
                            ),
                            rx.text(f"Vegan: {State.dinner_count_guests_vegan}"),
                            flex="1",
                        ),
                        rx.vstack(
                            rx.text.strong(
                                f"Volunteers eating dinner: {State.dinner_count_volunteers}"
                            ),
                            rx.text.strong(
                                f"Total served: {State.dinner_count_volunteers_served}",
                                **{"data-testid": "total-volunteers-served"},
                            ),
                            rx.text(f"Meat: {State.dinner_count_volunteers_meat}"),
                            rx.text(
                                f"Vegetarian: {State.dinner_count_volunteers_vegetarian}"
                            ),
                            rx.text(f"Vegan: {State.dinner_count_volunteers_vegan}"),
                            flex="1",
                        ),
                        spacing="4",
                        justify="between",
                        width="100%",
                    ),
                    rx.text("Loading..."),
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Name"),
                            rx.table.column_header_cell("Diet"),
                            rx.table.column_header_cell("Allergies"),
                            rx.table.column_header_cell("Volunteer"),
                            rx.table.column_header_cell("Served"),
                        )
                    ),
                    rx.table.body(rx.foreach(State.todays_dinner_meals, show_signup)),
                    variant="surface",
                    size="3",
                ),
            )
        )
    )


def admin_breakfast() -> rx.Component:
    return rx.container(
        rx.center(
            rx.vstack(
                rx.heading("Breakfast", size=default_heading_size),
                rx.vstack(admin_refresh_top_bar(), admin_last_update_message()),
                rx.cond(
                    ~State.is_loading_admin_meal_table,
                    rx.vstack(
                        rx.text.strong(
                            f"Total eating breakfast: {State.breakfast_count}"
                        ),
                        rx.text(
                            f"Total served: {State.breakfast_count_served}",
                            **{"data-testid": "total-served"},
                        ),
                        flex="1",
                    ),
                    rx.text("Loading..."),
                ),
                rx.scroll_area(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Name"),
                                rx.table.column_header_cell("Menu item"),
                                rx.table.column_header_cell("Allergies"),
                                rx.table.column_header_cell("Served"),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(State.todays_breakfast_meals, show_signup)
                        ),
                        variant="surface",
                        size="3",
                    ),
                    type="always",
                    scrollbars="vertical",
                    style={"height": "80vh"},
                ),
            )
        )
    )
