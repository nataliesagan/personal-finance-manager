"""Explainable expense categorisation engine.

This module is intentionally independent from Django models and from the ML model.
It provides a stable rule-based layer that keeps the project usable even when the
trained scikit-learn model is missing, outdated or uncertain.

The main idea is simple:
1. Normalize user text and bank descriptions.
2. Search a broad dictionary of Ukrainian, Russian and English keywords.
3. Return a category, confidence and a short human-readable explanation.
4. Let the ML layer be an optional addition, not a single point of failure.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

VALID_EXPENSE_CATEGORIES = {
    'food',
    'transport',
    'shopping',
    'entertainment',
    'bills',
    'health',
    'other',
}

CATEGORY_LABELS = {
    'food': 'Їжа та напої',
    'transport': 'Транспорт',
    'shopping': 'Шопінг',
    'entertainment': 'Розваги',
    'bills': 'Комуналка/рахунки',
    'health': 'Здоровʼя',
    'other': 'Інше',
}

# The lists below deliberately include simple words that users will test first:
# кава, торт, сукня, таксі, аптека, комуналка.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    'food': [
        'кава', 'кофе', 'coffee', 'cafe', 'кафе', 'старбакс', 'starbucks',
        'latte', 'лате', 'капучино', 'cappuccino', 'espresso', 'еспресо',
        'чай', 'tea', 'matcha', 'матча',
        'торт', 'cake', 'десерт', 'dessert', 'солодке', 'сладкое', 'цукерки',
        'конфеты', 'шоколад', 'булочка', 'круасан', 'croissant', 'донат', 'donut',
        'піца', 'pizza', 'суші', 'sushi', 'рол', 'roll', 'бургер', 'burger',
        'mcdonald', 'mcdonalds', 'макдональдс', 'kfc', 'subway', 'шаурма', 'донер',
        'їжа', 'еда', 'food', 'обід', 'обед', 'lunch', 'вечеря', 'ужин', 'dinner',
        'сніданок', 'завтрак', 'breakfast', 'restaurant', 'ресторан', 'їдальня',
        'продукти', 'продукты', 'groceries', 'grocery', 'supermarket', 'супермаркет',
        'атб', 'silpo', 'сільпо', 'novus', 'varus', 'metro', 'auchan', 'ашан',
        'еко маркет', 'fora', 'фора', 'товари для дому та їжі',
    ],
    'transport': [
        'таксі', 'taxi', 'uber', 'uklon', 'bolt', 'оплата таксі',
        'транспорт', 'transport', 'автобус', 'bus', 'метро квиток', 'metro ticket',
        'трамвай', 'tram', 'тролейбус', 'поїзд', 'поезд', 'train', 'укрзалізниця',
        'uz', 'залізниця', 'жд', 'квиток', 'билет', 'ticket transport',
        'паливо', 'топливо', 'бензин', 'diesel', 'gasoline', 'fuel', 'wog', 'okko',
        'socar', 'shell', 'брсм', 'azs', 'азс', 'парковка', 'parking', 'штраф парковка',
    ],
    'shopping': [
        'сукня', 'плаття', 'dress', 'одяг', 'одежда', 'clothes', 'clothing',
        'футболка', 'tshirt', 't shirt', 'сорочка', 'рубашка', 'куртка', 'coat',
        'джинси', 'джинсы', 'jeans', 'штани', 'брюки', 'pants', 'спідниця', 'юбка',
        'взуття', 'обувь', 'shoes', 'кросівки', 'кроссовки', 'sneakers', 'boots',
        'zara', 'bershka', 'stradivarius', 'pull bear', 'pullandbear', 'h m', 'hm',
        'reserved', 'sinsay', 'sinsey', 'cropp', 'house', 'mango', 'answear', 'intertop',
        'rozetka', 'розетка', 'makeup', 'eva', 'watsons', 'prostor', 'brocard',
        'shopping', 'шопінг', 'шопинг', 'покупки', 'покупка', 'замовлення', 'заказ',
        'aliexpress', 'amazon', 'ebay', 'temu', 'olx', 'prom ua', 'comfy', 'allo',
        'фокстрот', 'foxtrot', 'епіцентр', 'epicentr', 'jysk', 'ikea',
        'іграшки', 'игрушки', 'toy', 'toys', 'подарунок', 'подарок', 'gift',
    ],
    'entertainment': [
        'кіно', 'кино', 'cinema', 'movie', 'multiplex', 'planetakino', 'планета кіно',
        'netflix', 'spotify', 'youtube premium', 'megogo', 'sweet tv', 'apple music',
        'concert', 'концерт', 'театр', 'theatre', 'квитки на концерт',
        'bar', 'бар', 'pub', 'club', 'клуб', 'караоке', 'вечірка', 'вечеринка',
        'розваги', 'развлечения', 'entertainment', 'відпочинок', 'отдых',
        'steam', 'playstation', 'ps store', 'xbox', 'game', 'games', 'ігри', 'игры',
        'bowling', 'боулінг', 'квест', 'quest', 'парк розваг',
    ],
    'bills': [
        'комуналка', 'комунальні', 'коммуналка', 'коммунальные', 'utility', 'utilities',
        'рахунки', 'счета', 'bills', 'bill', 'оплата рахунку', 'оплата счета',
        'електроенергія', 'электроэнергия', 'electricity', 'світло', 'свет',
        'газ', 'gas bill', 'вода', 'water', 'водопостачання', 'водоснабжение',
        'інтернет', 'internet', 'wifi', 'провайдер', 'provider', 'volia', 'ланет',
        'мобільний', 'мобильный', 'mobile', 'lifecell', 'kyivstar', 'київстар',
        'vodafone', 'водафон', 'оренда', 'аренда', 'rent', 'квартплата', 'осбб',
        'страховка', 'insurance', 'податок', 'налог', 'tax',
    ],
    'health': [
        'аптека', 'аптеки', 'pharmacy', 'ліки', 'лекарства', 'medicine', 'medication',
        'таблетки', 'pills', 'антибіотик', 'антибиотик', 'вітаміни', 'витамины',
        'doctor', 'лікар', 'врач', 'терапевт', 'клініка', 'клиника', 'clinic',
        'лікарня', 'больница', 'hospital', 'здоров’я', 'здоровье', 'health',
        'optika', 'оптика', 'окуляри', 'очки', 'стоматолог', 'dentist', 'dental',
        'лабораторія', 'лаборатория', 'аналізи', 'анализы', 'діагностика', 'диагностика',
        'helsi', 'добробут', 'synevo', 'сінево', 'інвітро', 'медична', 'медицинская',
    ],
}

# Some bank exports use category names instead of useful descriptions. This mapping
# handles such cases before keyword scoring.
CATEGORY_ALIASES = {
    'їжа': 'food',
    'їжа та напої': 'food',
    'еда': 'food',
    'еда и напитки': 'food',
    'food': 'food',
    'groceries': 'food',
    'продукти': 'food',
    'transport': 'transport',
    'транспорт': 'transport',
    'таксі': 'transport',
    'taxi': 'transport',
    'shopping': 'shopping',
    'шопінг': 'shopping',
    'шопинг': 'shopping',
    'покупки': 'shopping',
    'одяг': 'shopping',
    'одежда': 'shopping',
    'entertainment': 'entertainment',
    'розваги': 'entertainment',
    'развлечения': 'entertainment',
    'bills': 'bills',
    'комуналка': 'bills',
    'комунальні': 'bills',
    'рахунки': 'bills',
    'счета': 'bills',
    'health': 'health',
    'здоровʼя': 'health',
    'здоров’я': 'health',
    'здоровье': 'health',
    'аптека': 'health',
    'other': 'other',
    'інше': 'other',
    'другое': 'other',
}

@dataclass(frozen=True)
class CategoryDecision:
    category: str
    confidence: float
    source: str
    matched_keywords: tuple[str, ...] = ()
    explanation: str = ''

    @property
    def label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category)


def normalize_text(text: object) -> str:
    value = str(text or '').lower()
    value = value.replace('ʼ', "'").replace('’', "'").replace('`', "'")
    value = value.replace('&', ' and ')
    value = re.sub(r'[^a-zа-яіїєґ0-9\s\']+', ' ', value, flags=re.IGNORECASE)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def tokenize(text: object) -> set[str]:
    normalized = normalize_text(text)
    if not normalized:
        return set()
    return set(normalized.split())


def normalize_category(category: object) -> str:
    normalized = normalize_text(category)
    if not normalized:
        return 'other'
    if normalized in VALID_EXPENSE_CATEGORIES:
        return normalized
    return CATEGORY_ALIASES.get(normalized, 'other')


def _keyword_score(text: str, keyword: str) -> int:
    text_norm = normalize_text(text)
    key_norm = normalize_text(keyword)
    if not text_norm or not key_norm:
        return 0

    padded_text = f' {text_norm} '
    padded_key = f' {key_norm} '

    if padded_key in padded_text:
        return 6 if ' ' in key_norm else 5
    if key_norm in text_norm:
        return 2
    return 0


def predict_by_keywords(text: object, extra_texts: Iterable[object] | None = None) -> CategoryDecision:
    parts = [str(text or '')]
    if extra_texts:
        parts.extend(str(item or '') for item in extra_texts if item)
    combined = ' '.join(parts)
    normalized = normalize_text(combined)

    if not normalized:
        return CategoryDecision('other', 0.0, 'empty', (), 'Текст операції порожній.')

    scores: dict[str, int] = {category: 0 for category in VALID_EXPENSE_CATEGORIES}
    matches: dict[str, list[str]] = {category: [] for category in VALID_EXPENSE_CATEGORIES}

    alias_category = normalize_category(normalized)
    if alias_category != 'other':
        return CategoryDecision(
            alias_category,
            0.98,
            'category_alias',
            (normalized,),
            f'Категорію визначено за готовою назвою категорії: {CATEGORY_LABELS[alias_category]}.',
        )

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            score = _keyword_score(normalized, keyword)
            if score:
                scores[category] += score
                matches[category].append(keyword)

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]

    if best_score <= 0:
        return CategoryDecision(
            'other',
            0.0,
            'no_match',
            (),
            'Не знайдено ключових слів для автоматичної категоризації.',
        )

    second_score = sorted(scores.values(), reverse=True)[1]
    unique_matches = tuple(list(dict.fromkeys(matches[best_category]))[:5])

    if best_score >= 10 or best_score - second_score >= 6:
        confidence = 0.96
    elif best_score >= 5:
        confidence = 0.88
    else:
        confidence = 0.72

    matched_text = ', '.join(unique_matches)
    explanation = (
        f'Категорію “{CATEGORY_LABELS[best_category]}” визначено за ключовими словами: {matched_text}.'
        if matched_text else
        f'Категорію “{CATEGORY_LABELS[best_category]}” визначено за словниковими правилами.'
    )

    return CategoryDecision(
        best_category,
        confidence,
        'keyword_rules',
        unique_matches,
        explanation,
    )


def choose_best_decision(keyword_decision: CategoryDecision, ml_category: str | None, ml_confidence: float | None) -> CategoryDecision:
    ml_category = normalize_category(ml_category)
    ml_confidence = float(ml_confidence or 0.0)

    if keyword_decision.category != 'other':
        return keyword_decision

    if ml_category != 'other' and ml_confidence >= 0.45:
        return CategoryDecision(
            ml_category,
            ml_confidence,
            'ml_model',
            (),
            f'Категорію “{CATEGORY_LABELS[ml_category]}” визначено ML-моделлю.',
        )

    return CategoryDecision(
        'other',
        max(keyword_decision.confidence, ml_confidence),
        'fallback_other',
        (),
        'Категорію не вдалося визначити автоматично, тому встановлено “Інше”.',
    )
