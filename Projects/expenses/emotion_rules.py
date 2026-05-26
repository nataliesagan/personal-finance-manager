from datetime import time


FAST_FOOD_KEYWORDS = [
    'mcdonald', 'mcdonalds', 'kfc', 'burger', 'pizza', 'subway',
    'донер', 'шаурма', 'фастфуд', 'кава', 'coffee', 'starbucks',
    'latte', 'капучино', 'espresso', 'sushi', 'roll', 'макдональдс'
]

ONLINE_SHOPPING_KEYWORDS = [
    'aliexpress', 'amazon', 'ebay', 'rozetka', 'ozon',
    'steam', 'playstation', 'xbox', 'g2a', 'makeup', 'sinsey',
    'shopping', 'замовлення', 'покупка онлайн'
]

ENTERTAINMENT_KEYWORDS = [
    'cinema', 'movie', 'netflix', 'spotify', 'concert',
    'pub', 'bar', 'club', 'кіно', 'караоке', 'вечірка'
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    text = (text or '').lower()
    return any(k in text for k in keywords)


def analyze_emotional_expense(description: str, category: str, dt) -> tuple[bool, str]:
    desc = (description or '').lower()
    category = (category or 'other').lower()

    if _contains_any(desc, FAST_FOOD_KEYWORDS):
        return True, 'fast_food'

    if _contains_any(desc, ONLINE_SHOPPING_KEYWORDS):
        return True, 'online_shopping'

    if _contains_any(desc, ENTERTAINMENT_KEYWORDS) or category == 'entertainment':
        if dt.time() >= time(20, 0) or dt.time() <= time(6, 0):
            return True, 'late_night'
        return True, 'entertainment'

    if category in ['food', 'shopping'] and (dt.time() >= time(21, 0) or dt.time() <= time(5, 0)):
        return True, 'late_night'

    return False, 'none'