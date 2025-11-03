import asyncio
import html
import json
import logging
import os
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv(".env")

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("ADMIN_IDS", "").split(",")
    if user_id.strip().isdigit()
}
SHOP_WEB_APP_URL = os.getenv("SHOP_WEB_APP_URL")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


QUESTIONS = [
    {
        "question": "Ваш пол",
        "options": ["м", "ж"],
    },
    {
        "question": "Возраст",
        "options": ["<12", "12-18", "19-25", "26-35", "36-45", "45+"],
    },
    {
        "question": "Беременность",
        "options": ["да", "нет"],
    },
    {
        "question": "Часто ли бывает чувство жжения, покраснения, реакции на смену погоды или новые средства?",
        "options": ["да", "нет"],
    },
    {
        "question": "Есть ли на коже жирный блеск?",
        "options": ["да", "нет"],
    },
    {
        "question": "Опишите состояние ваших пор",
        "options": ["расширены на всем лице", "расширены в т-зоне", "не расширены"],
    },
    {
        "question": "Замечаете ли вы сухость и стянутость кожи?",
        "options": ["да", "нет"],
    },
    {
        "question": "Есть ли у вас прыщи/черные точки?",
        "options": ["да, больше прыщей", "да, больше черных точек", "нет"],
    },
    {
        "question": "Есть ли у вас пигментация, шрамы, рубцы, постакне?",
        "options": [
            "да, больше беспокоит пигментация",
            "да, больше беспокоят постакне/рубцы",
            "нет",
        ],
    },
    {
        "question": "Есть ли у вас морщины, потеря упругости?",
        "options": ["да", "нет"],
    },
    {
        "question": "Достаточно ли коже увлажнения?",
        "options": ["да", "нет"],
    },
    {
        "question": "Какую задачу вы хотели бы решить?",
        "options": [
            "убрать высыпания",
            "убрать жирный блеск",
            "поработать с морщинами",
            "убрать пигментацию",
            "увлажнить кожу",
            "убрать чувствительность",
        ],
        "multiple": True,
    },
]


class TestStates(StatesGroup):
    in_progress = State()


def ensure_answers_capacity(answers: list, upto_idx: int) -> None:
    while len(answers) <= upto_idx:
        question = QUESTIONS[len(answers)]
        answers.append([] if question.get("multiple") else None)


def main_keyboard(user_telegram_id: int) -> ReplyKeyboardMarkup:
    shop_button = (
        KeyboardButton(text="🛒 Магазин", web_app=WebAppInfo(url=SHOP_WEB_APP_URL))
        if SHOP_WEB_APP_URL
        else KeyboardButton(text="🛒 Магазин")
    )

    buttons = [
        [KeyboardButton(text="🧴 Подобрать уход"), KeyboardButton(text="🗓️ Запись")],
        [shop_button, KeyboardButton(text="❓ Помощь")],
    ]

    if user_telegram_id in ADMIN_IDS:
        buttons.append([KeyboardButton(text="⚙️ Админ панель")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False,  # keep buttons visible after re-entering the chat
        input_field_placeholder="Воспользуйтесь меню:",
    )


def build_question_keyboard(question_idx: int, selected_options=None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    question = QUESTIONS[question_idx]

    if question.get("multiple"):
        selected_options = selected_options or []
        for option_idx, option in enumerate(question["options"]):
            is_selected = option in selected_options
            label = f"{'✅ ' if is_selected else ''}{option}"
            builder.button(text=label, callback_data=f"toggle:{question_idx}:{option_idx}")
        builder.button(text="✅ Готово", callback_data=f"next:{question_idx}")
    else:
        for option_idx, option in enumerate(question["options"]):
            builder.button(text=option, callback_data=f"answer:{question_idx}:{option_idx}")

    builder.adjust(1)
    return builder.as_markup()


async def send_question(message: Message, question_idx: int, state: FSMContext) -> None:
    question = QUESTIONS[question_idx]
    data = await state.get_data()
    answers = data.get("answers", [])

    selected_options = None
    if question.get("multiple") and len(answers) > question_idx:
        stored_value = answers[question_idx]
        if isinstance(stored_value, list):
            selected_options = stored_value

    keyboard = build_question_keyboard(question_idx, selected_options)
    text = f"<b>{question_idx + 1}) {question['question']}</b>"
    await message.answer(text, reply_markup=keyboard)


async def start(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    await message.answer("Привет! Выберите интересующую опцию:", reply_markup=main_keyboard(user_id))


async def restart_test(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(TestStates.in_progress)
    await state.update_data(answers=[], current_question=0)
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_question(callback.message, 0, state)


async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    action = parts[0]
    question_idx = int(parts[1])
    question = QUESTIONS[question_idx]

    data = await state.get_data()
    answers = data.get("answers", [])
    current_index = data.get("current_question", 0)

    if question_idx != current_index:
        logger.warning("Unexpected question index order. Expected %s, got %s.", current_index, question_idx)
        current_index = question_idx

    ensure_answers_capacity(answers, question_idx)

    if action == "toggle":
        option_idx = int(parts[2])
        selected_option = question["options"][option_idx]
        current_value = answers[question_idx]
        if not isinstance(current_value, list):
            current_value = []

        if selected_option in current_value:
            current_value.remove(selected_option)
        else:
            current_value.append(selected_option)

        answers[question_idx] = current_value
        await state.update_data(answers=answers, current_question=question_idx)
        keyboard = build_question_keyboard(question_idx, current_value)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
        return

    advance = False

    if action == "answer":
        option_idx = int(parts[2])
        selected_option = question["options"][option_idx]
        answers[question_idx] = selected_option
        advance = True
    elif action == "next":
        current_value = answers[question_idx]
        if not isinstance(current_value, list) or not current_value:
            await callback.answer("Выберите хотя бы один вариант.", show_alert=True)
            return
        advance = True
    else:
        await callback.answer("Неизвестное действие.", show_alert=True)
        return

    if not advance:
        await callback.answer()
        return

    next_index = question_idx + 1
    await state.update_data(answers=answers, current_question=next_index)

    await callback.message.edit_reply_markup(reply_markup=None)

    if next_index < len(QUESTIONS):
        await callback.answer()
        await send_question(callback.message, next_index, state)
        return

    summary_lines = ["Спасибо! Ваши ответы:"]
    for idx, answer in enumerate(answers, start=1):
        if isinstance(answer, list):
            answer_text = ", ".join(answer) if answer else "—"
        elif answer:
            answer_text = str(answer)
        else:
            answer_text = "—"
        summary_lines.append(f"<b>{idx})</b>   <i>{answer_text}</i>")
    summary_text = "\n".join(summary_lines)

    restart_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать заново", callback_data="restart_test")]]
    )

    await callback.answer()
    await callback.message.answer(summary_text, reply_markup=restart_keyboard)
    await state.clear()


async def handle_booking_request(message: Message) -> None:
    await message.answer("Онлайн-запись появится совсем скоро. Спасибо за ожидание!")


async def show_shop(message: Message) -> None:
    if not SHOP_WEB_APP_URL:
        await message.answer(
            "Магазин временно недоступен. Пожалуйста, попробуйте позже."
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть мини-магазин",
                    web_app=WebAppInfo(url=SHOP_WEB_APP_URL),
                )
            ]
        ]
    )

    await message.answer(
        "Жмите на кнопку ниже, чтобы открыть мини-магазин и оформить заказ.",
        reply_markup=keyboard,
    )


async def handle_shop_order(message: Message) -> None:
    if not message.web_app_data or not message.web_app_data.data:
        await message.answer("Не удалось получить данные заказа.")
        return

    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        logger.exception("Failed to decode web_app_data payload: %s", message.web_app_data.data)
        await message.answer("Произошла ошибка при обработке заказа.")
        return

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        await message.answer("Похоже, корзина была пустой — заказ не создан.")
        return

    def _to_decimal(value) -> Decimal | None:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    order_lines = []
    total_calculated = Decimal("0")

    for idx, raw_item in enumerate(items, start=1):
        name = str(raw_item.get("name", "Без названия"))
        quantity_raw = raw_item.get("quantity", 0)
        try:
            quantity = int(quantity_raw)
        except (TypeError, ValueError):
            quantity = 0

        price = _to_decimal(raw_item.get("price")) or Decimal("0")
        line_total = price * quantity
        total_calculated += line_total

        order_lines.append(
            f"{idx}. {html.escape(name)} — {quantity} шт. x ${price:.2f} = ${line_total:.2f}"
        )

    declared_total = _to_decimal(payload.get("totalPrice"))
    total_display = declared_total if declared_total is not None else total_calculated

    if declared_total is not None and abs(declared_total - total_calculated) > Decimal("0.01"):
        logger.warning(
            "Order total mismatch for user %s: declared %s vs calculated %s",
            message.from_user.id if message.from_user else "unknown",
            declared_total,
            total_calculated,
        )
        order_lines.append(
            f"Пересчитанная сумма: ${total_calculated:.2f} (передано: ${declared_total:.2f})"
        )
        total_display = total_calculated

    order_text = "\n".join(order_lines)
    user_note = (
        "<b>Спасибо!</b>\n"
        "Запрос на оформление заказа передан.\n\n"
        f"{order_text}\n"
        f"<b>Итого:</b> ${total_display:.2f}"
    )
    await message.answer(user_note)

    if ADMIN_IDS:
        user = message.from_user
        user_link = "неизвестный покупатель"
        if user:
            escaped_name = html.escape(user.full_name or str(user.id))
            user_link = f"<a href='tg://user?id={user.id}'>{escaped_name}</a>"

        admin_text = (
            f"🛒 <b>Новый заказ</b>\n"
            f"Покупатель: {user_link}\n"
            f"{order_text}\n"
            f"<b>Итого:</b> ${total_display:.2f}"
        )

        for admin_id in ADMIN_IDS:
            if user and admin_id == user.id:
                continue
            try:
                await message.bot.send_message(admin_id, admin_text)
            except Exception:
                logger.exception("Failed to notify admin %s about new order.", admin_id)


async def show_help(message: Message) -> None:
    help_text = (
        "<b>Нужна подсказка?</b>\n\n"
        "Вы можете подобрать уход в зависимости от того, насколько хорошо понимаете особенности своей кожи:\n"
        "• <b>Подобрать уход</b> — тест на определение типа кожи и профессиональные рекомендации.\n"
        "• <b>Запись</b> — перейдите сюда, если хотите сразу пообщаться с косметологом.\n"
        "• <b>Магазин</b> — загляните, чтобы заказать конкретное средство."
    )
    await message.answer(help_text)


async def show_admin_panel(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    if user_id in ADMIN_IDS:
        await message.answer("Админ-панель пока что пуста, но мы уже над ней работаем.")
    else:
        await message.answer("У вас нет доступа к админ-панели.")


async def handle_fill_form(message: Message, state: FSMContext) -> None:
    await state.set_state(TestStates.in_progress)
    await state.update_data(answers=[], current_question=0)
    await send_question(message, 0, state)


async def main() -> None:
    if not TOKEN:
        raise RuntimeError("Не удалось получить TOKEN из переменных окружения.")

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(start, CommandStart())
    dp.message.register(handle_shop_order, F.web_app_data)
    dp.message.register(handle_fill_form, F.text == "🧴 Подобрать уход")
    dp.message.register(handle_booking_request, F.text == "🗓️ Запись")
    dp.message.register(show_shop, F.text == "🛒 Магазин")
    dp.message.register(show_help, F.text == "❓ Помощь")
    dp.message.register(show_admin_panel, F.text == "⚙️ Админ панель")
    dp.callback_query.register(restart_test, F.data == "restart_test")
    dp.callback_query.register(handle_answer, F.data.regexp(r"^(answer|toggle|next):"))

    logger.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
