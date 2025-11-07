from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_quality_keyboard(video_id: str, variants: list[tuple[str, str]]):
    builder = InlineKeyboardBuilder()
    for format_id, label in variants:
        builder.button(text=label, callback_data=f"q:{video_id}:{format_id}:{label}")
    builder.adjust(3)
    return builder.as_markup()



