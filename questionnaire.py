from __future__ import annotations

import logging
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)


class AnswerVariant:
    def __init__(self, text: str, product: str) -> None:
        self.text = text
        self.product = product

    def get_product(self) -> str:
        return self.product


class Question:
    def __init__(
        self,
        code: str,
        text: str,
        options: list[AnswerVariant],
        multiple: bool = False,
        default_next_question: Question | None = None,
    ) -> None:
        self.code = code
        self.text = text
        self.options = options
        self.multiple = multiple
        self.default_next_question = default_next_question

    def get_next_question(self, selected_answers: list[AnswerVariant]) -> Question | None:
        return self.default_next_question


class YourSexQuestion(Question):
    def __init__(
        self,
        code: str,
        text: str,
        options: list[AnswerVariant],
        default_next_question: Question,
        male_next_question: Question,
    ) -> None:
        super().__init__(code, text, options, multiple=False, default_next_question=default_next_question)
        self.male_next_question = male_next_question

    def get_next_question(self, selected_answers: list[AnswerVariant]) -> Question | None:
        if selected_answers and selected_answers[0].text == "Мужской":
            return self.male_next_question
        return self.default_next_question


class AgeQuestion(Question):
    def __init__(
        self,
        code: str,
        text: str,
        options: list[AnswerVariant],
        underage_next_question: Question,
        default_next_question: Question,
    ) -> None:
        super().__init__(code, text, options, multiple=False, default_next_question=default_next_question)
        self.underage_next_question = underage_next_question

    def get_next_question(self, selected_answers: list[AnswerVariant]) -> Question | None:
        if selected_answers and selected_answers[0].text in ("<12", "12-18"):
            return self.underage_next_question
        return self.default_next_question


class QuestionnaireSession:
    def __init__(self, first_question: Question, question_map: dict[str, Question]) -> None:
        self.current_question: Question | None = first_question
        self.answers: dict[str, AnswerVariant | list[AnswerVariant] | None] = {}
        self.asked_order: list[str] = []
        self.question_map = question_map
        self.male_selected = False
        self.pregnancy_warning_sent = False
        self.age_warning_sent = False

    def record_selection(self, question: Question, selected_answers: list[AnswerVariant], advance: bool) -> None:
        if question.code == "q1" and selected_answers and selected_answers[0].text == "Мужской":
            self.male_selected = True

        if question.multiple:
            self.answers[question.code] = selected_answers
        else:
            self.answers[question.code] = selected_answers[0] if selected_answers else None

        if question.code not in self.asked_order:
            self.asked_order.append(question.code)

        next_question = question.get_next_question(selected_answers) if advance else question

        if self.male_selected and next_question and next_question.code == "q8":
            next_question = next_question.default_next_question

        self.current_question = next_question

    def get_selected_answers(self, question: Question) -> list[AnswerVariant]:
        stored = self.answers.get(question.code)
        if question.multiple:
            return list(stored) if isinstance(stored, list) else []
        if isinstance(stored, AnswerVariant):
            return [stored]
        return []


def build_questionnaire_session() -> QuestionnaireSession:
    q11 = Question(
        code="q11",
        text="Какую задачу вы хотели бы решить?",
        options=[
            AnswerVariant("Убрать высыпания", ""),
            AnswerVariant("Убрать жирный блеск", ""),
            AnswerVariant("Поработать с морщинами", ""),
            AnswerVariant("Убрать пигментацию", "Vita C Serum"),
            AnswerVariant("Увлажнить кожу", "Сыворотка HYDRA"),
            AnswerVariant("Убрать чувствительность", "Сыворотка CR"),
        ],
        multiple=True,
        default_next_question=None,
    )
    q10 = Question(
        code="q10",
        text="Есть ли у вас морщины, потеря упругости?",
        options=[AnswerVariant("Да", "AGE Recovery"), AnswerVariant("Нет", "")],
        default_next_question=q11,
    )
    q9 = Question(
        code="q9",
        text="Есть ли у вас пигментация, шрамы, рубцы, постакне?",
        options=[
            AnswerVariant("Да, больше беспокоит пигментация", "MELA Recovery"),
            AnswerVariant("Да, больше беспокоят постакне/рубцы", "RETISOLVE"),
            AnswerVariant("Нет", ""),
        ],
        default_next_question=q10,
    )
    q8 = Question(
        code="q8",
        text="Есть ли у вас прыщи/черные точки?",
        options=[
            AnswerVariant("Да, больше прыщей", "Вита В3 крем"),
            AnswerVariant("Да, больше черных точек", "Ламеллярный крем для комби кожи"),
            AnswerVariant("Нет", "Пост рекавери крем"),
        ],
        default_next_question=q9,
    )
    q7 = Question(
        code="q7",
        text="Замечаете ли вы сухость и стянутость кожи?",
        options=[AnswerVariant("Да", "Мист микробиом"), AnswerVariant("Нет", "")],
        default_next_question=q8,
    )
    q6 = Question(
        code="q6",
        text="Опишите состояние ваших пор",
        options=[
            AnswerVariant("Расширены на всем лице", ""),
            AnswerVariant("Расширены в т-зоне", ""),
            AnswerVariant("Не расширены", ""),
        ],
        default_next_question=q7,
    )
    q5 = Question(
        code="q5",
        text="Есть ли на коже жирный блеск?",
        options=[AnswerVariant("Да", "Тоник SALIBIOME"), AnswerVariant("Нет", "")],
        default_next_question=q6,
    )
    q4 = Question(
        code="q4",
        text="Часто ли бывает чувство жжения, покраснения, реакции на смену погоды или новые средства?",
        options=[
            AnswerVariant("Да", "Гель для умывания VELVET CLEANSER"),
            AnswerVariant("Нет", "Гель для умывания  EXFO CLEANSE"),
        ],
        default_next_question=q5,
    )
    q3 = Question(
        code="q3",
        text="Беременность",
        options=[AnswerVariant("Да", ""), AnswerVariant("Нет", "")],
        default_next_question=q4,
    )
    q2 = AgeQuestion(
        code="q2",
        text="Возраст",
        options=[
            AnswerVariant("<12", ""),
            AnswerVariant("12-18", ""),
            AnswerVariant("19-25", ""),
            AnswerVariant("26-35", ""),
            AnswerVariant("36-45", ""),
            AnswerVariant("45+", ""),
        ],
        underage_next_question=q4,
        default_next_question=q3,
    )
    q1 = YourSexQuestion(
        code="q1",
        text="Ваш пол",
        options=[AnswerVariant("Мужской", ""), AnswerVariant("Женский", "")],
        default_next_question=q2,
        male_next_question=q4,
    )

    question_map = {q.code: q for q in [q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11]}
    return QuestionnaireSession(first_question=q1, question_map=question_map)


class TestStates(StatesGroup):
    in_progress = State()


def _validate_list_answer(answer: Any) -> list[AnswerVariant]:
    if isinstance(answer, list):
        return answer
    return []


def build_question_keyboard(question: Question, selected_options: list[AnswerVariant] | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    selected_options = selected_options or []

    if question.multiple:
        for option_idx, option in enumerate(question.options):
            is_selected = option in selected_options
            label = f"{'✅ ' if is_selected else ''}{option.text}"
            builder.button(text=label, callback_data=f"toggle:{question.code}:{option_idx}")
        builder.button(text="✅ Готово", callback_data=f"next:{question.code}")
    else:
        for option_idx, option in enumerate(question.options):
            builder.button(text=option.text, callback_data=f"answer:{question.code}:{option_idx}")

    builder.adjust(1)
    return builder.as_markup()


async def send_question(message: Message, session: QuestionnaireSession) -> None:
    question = session.current_question
    if question is None:
        logger.warning("Attempted to send a question but session is already complete.")
        return

    selected_options = session.get_selected_answers(question)
    keyboard = build_question_keyboard(question, selected_options)
    question_number = len(session.asked_order) + 1
    text = f"<b>{question_number}) {question.text}</b>"
    await message.answer(text, reply_markup=keyboard)


async def restart_test(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    session = build_questionnaire_session()
    await state.set_state(TestStates.in_progress)
    await state.update_data(session=session)
    await callback.message.edit_reply_markup(reply_markup=None)
    await send_question(callback.message, session)


async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    session: QuestionnaireSession | None = data.get("session")

    if session is None or session.current_question is None:
        await callback.answer("Сессия устарела, начните заново.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer("Некорректные данные ответа.", show_alert=True)
        return

    action, question_code = parts[0], parts[1]
    question = session.question_map.get(question_code)

    if question is None:
        await callback.answer("Вопрос не найден, начните заново.", show_alert=True)
        return

    if question != session.current_question:
        logger.warning("Unexpected question order. Expected %s, got %s.", session.current_question.code, question_code)
        await callback.answer("Этот вопрос уже пройден.", show_alert=True)
        return

    if action == "toggle":
        if len(parts) < 3:
            await callback.answer("Некорректные данные ответа.", show_alert=True)
            return
        option_idx = int(parts[2])
        selected_option = question.options[option_idx]
        current_selection = session.get_selected_answers(question)

        if selected_option in current_selection:
            current_selection.remove(selected_option)
        else:
            current_selection.append(selected_option)

        session.record_selection(question, current_selection, advance=False)
        await state.update_data(session=session)
        keyboard = build_question_keyboard(question, current_selection)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
        return

    advance = False

    if action == "answer":
        if len(parts) < 3:
            await callback.answer("Некорректные данные ответа.", show_alert=True)
            return
        option_idx = int(parts[2])
        selected_option = question.options[option_idx]
        session.record_selection(question, [selected_option], advance=True)
        advance = True
        if (
            question.code == "q2"
            and selected_option.text in ("<12", "12-18")
            and not session.age_warning_sent
        ):
            session.age_warning_sent = True
            warning_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Записаться на прием", callback_data="book_appointment")]
                ]
            )
            await callback.message.answer(
                "Обращаем ваше внимание! Данная ситуация требует обязательной консультации у косметолога!",
                reply_markup=warning_keyboard,
            )
        if (
            question.code == "q3"
            and selected_option.text == "Да"
            and not session.pregnancy_warning_sent
        ):
            session.pregnancy_warning_sent = True
            warning_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Записаться на прием", callback_data="book_appointment")]
                ]
            )
            await callback.message.answer(
                "Обращаем ваше внимание! Данная ситуация требует обязательной консультации у косметолога!",
                reply_markup=warning_keyboard,
            )
    elif action == "next":
        current_value = _validate_list_answer(session.answers.get(question.code))
        if not current_value:
            await callback.answer("Выберите хотя бы один вариант.", show_alert=True)
            return
        session.record_selection(question, current_value, advance=True)
        advance = True
    else:
        await callback.answer("Неизвестное действие.", show_alert=True)
        return

    if not advance:
        await callback.answer()
        return

    await state.update_data(session=session)
    await callback.message.edit_reply_markup(reply_markup=None)

    if session.current_question is not None:
        await callback.answer()
        await send_question(callback.message, session)
        return

    products: list[str] = []
    for stored_answer in session.answers.values():
        if isinstance(stored_answer, list):
            for answer in stored_answer:
                if answer.product and answer.product not in products:
                    products.append(answer.product)
        elif isinstance(stored_answer, AnswerVariant) and stored_answer.product:
            if stored_answer.product not in products:
                products.append(stored_answer.product)

    summary_lines = [
        "Спасибо! На основе ваших ответов, вам подойдут следующие продукты для ухода за кожей:"
    ]
    if products:
        for product in products:
            summary_lines.append(f"• {product}")
    else:
        summary_lines.append("Пока не удалось подобрать продукты.")

    summary_text = "\n".join(summary_lines)

    restart_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать заново", callback_data="restart_test")]]
    )

    await callback.answer()
    await callback.message.answer(summary_text, reply_markup=restart_keyboard)
    await state.clear()


async def handle_fill_form(message: Message, state: FSMContext) -> None:
    session = build_questionnaire_session()
    await state.set_state(TestStates.in_progress)
    await state.update_data(session=session)
    await send_question(message, session)
