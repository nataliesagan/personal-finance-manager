from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from expenses.services.category_engine import normalize_text

FAST_FOOD_KEYWORDS = [
    'mcdonald', 'mcdonalds', 'макдональдс', 'kfc', 'burger', 'бургер',
    'pizza', 'піца', 'subway', 'донер', 'шаурма', 'фастфуд',
    'кава', 'кофе', 'coffee', 'кафе', 'cafe', 'starbucks',
    'latte', 'лате', 'капучино', 'cappuccino', 'espresso', 'еспресо',
    'торт', 'cake', 'десерт', 'dessert', 'солодке', 'сладкое',
    'цукерки', 'конфеты', 'шоколад', 'donut', 'донат', 'булочка', 'круасан',
    'sushi', 'суші', 'roll', 'рол',
]

ONLINE_SHOPPING_KEYWORDS = [
    'aliexpress', 'amazon', 'ebay', 'temu', 'rozetka', 'розетка', 'prom ua',
    'ozon', 'steam', 'playstation', 'ps store', 'xbox', 'g2a',
    'makeup', 'eva', 'watsons', 'brocard', 'sinsay', 'sinsey', 'zara',
    'shopping', 'шопінг', 'шопинг', 'замовлення', 'заказ', 'покупка онлайн',
    'онлайн покупка', 'онлайн-замовлення', 'онлайн заказ',
]

ENTERTAINMENT_KEYWORDS = [
    'cinema', 'movie', 'multiplex', 'планета кіно', 'netflix', 'spotify',
    'concert', 'концерт', 'pub', 'bar', 'club', 'кіно', 'кино', 'караоке',
    'вечірка', 'вечеринка', 'розваги', 'развлечения', 'театр', 'theatre',
]

EMOTIONAL_CATEGORY_TAGS = {
    'entertainment': 'entertainment',
}

@dataclass(frozen=True)
class EmotionalDecision:
    is_emotional: bool
    tag: str
    reason: str
    matched_keyword: str | None = None


def _first_keyword(text: str, keywords: list[str]) -> str | None:
    normalized = normalize_text(text)
    for keyword in keywords:
        key = normalize_text(keyword)
        if key and key in normalized:
            return keyword
    return None


def _is_late(dt) -> bool:
    return dt.time() >= time(21, 0) or dt.time() <= time(5, 0)


def analyze_emotional_expense_details(description: str, category: str, dt) -> EmotionalDecision:
    desc = description or ''
    category = (category or 'other').lower()

    keyword = _first_keyword(desc, FAST_FOOD_KEYWORDS)
    if keyword:
        return EmotionalDecision(
            True,
            'fast_food',
            f'Позначено як емоційну витрату, тому що знайдено ознаку імпульсивної їжі або кави: {keyword}.',
            keyword,
        )

    keyword = _first_keyword(desc, ONLINE_SHOPPING_KEYWORDS)
    if keyword:
        return EmotionalDecision(
            True,
            'online_shopping',
            f'Позначено як емоційну витрату, тому що знайдено ознаку онлайн-шопінгу: {keyword}.',
            keyword,
        )

    keyword = _first_keyword(desc, ENTERTAINMENT_KEYWORDS)
    if keyword:
        if _is_late(dt):
            return EmotionalDecision(
                True,
                'late_night',
                f'Позначено як пізню емоційну витрату, тому що знайдено ознаку розваг: {keyword}.',
                keyword,
            )
        return EmotionalDecision(
            True,
            'entertainment',
            f'Позначено як емоційну витрату, тому що знайдено ознаку розваг: {keyword}.',
            keyword,
        )

    if category in EMOTIONAL_CATEGORY_TAGS:
        if _is_late(dt):
            return EmotionalDecision(
                True,
                'late_night',
                'Позначено як пізню емоційну витрату через категорію розваг і вечірній або нічний час.',
            )
        return EmotionalDecision(
            True,
            EMOTIONAL_CATEGORY_TAGS[category],
            'Позначено як емоційну витрату через категорію розваг.',
        )

    if category in ['food', 'shopping'] and _is_late(dt):
        return EmotionalDecision(
            True,
            'late_night',
            'Позначено як емоційну витрату через вечірній або нічний час для їжі чи шопінгу.',
        )

    return EmotionalDecision(
        False,
        'none',
        'Ознак емоційної витрати не знайдено.',
    )


def analyze_emotional_expense(description: str, category: str, dt) -> tuple[bool, str]:
    decision = analyze_emotional_expense_details(description, category, dt)
    return decision.is_emotional, decision.tag
