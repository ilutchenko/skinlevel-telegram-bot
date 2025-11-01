import asyncio
import logging
import os

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
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

load_dotenv(".env")

TOKEN = os.getenv("TOKEN")
ADMIN_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("ADMIN_IDS", "").split(",")
    if user_id.strip().isdigit()
}

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
    buttons = [
        [KeyboardButton(text="🧴 Подобрать уход"), KeyboardButton(text="🗓️ Запись")],
        [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="❓ Помощь")],
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
    await message.answer("Магазин готовится к запуску. Следите за новостями.")


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
