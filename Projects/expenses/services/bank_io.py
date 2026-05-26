import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from ..emotion_rules import analyze_emotional_expense
from ..models import Expense, Income
from ..ml.expense_classifier import predict_category


DATE_FORMATS = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%d.%m.%Y %H:%M:%S',
    '%d.%m.%Y %H:%M',
    '%d.%m.%Y',
    '%d/%m/%Y %H:%M:%S',
    '%d/%m/%Y %H:%M',
    '%d/%m/%Y',
]


@dataclass
class ParsedTransaction:
    occurred_at: datetime
    amount: Decimal
    description: str
    direction: str
    category: str | None
    raw_source: str


def _normalize_header(value: str) -> str:
    return ''.join(ch for ch in (value or '').strip().lower() if ch.isalnum())


def _sniff_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
        return dialect.delimiter
    except csv.Error:
        if sample.count(';') >= sample.count(','):
            return ';'
        return ','


def _as_decimal(value: str) -> Decimal:
    cleaned = (value or '').strip().replace(' ', '').replace('\xa0', '')
    cleaned = cleaned.replace(',', '.')
    if not cleaned:
        raise InvalidOperation('empty amount')
    return Decimal(cleaned)


def _parse_date(date_value: str, time_value: str = '') -> datetime:
    date_value = (date_value or '').strip()
    time_value = (time_value or '').strip()
    combined = f'{date_value} {time_value}'.strip()

    for candidate in [combined, date_value]:
        if not candidate:
            continue
        for fmt in DATE_FORMATS:
            try:
                dt = datetime.strptime(candidate, fmt)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                return dt
            except ValueError:
                continue

    raise ValueError(f'Неможливо розпізнати дату: {combined or date_value}')


def _choose_value(row: dict, normalized_map: dict, variants: list[str], default: str = '') -> str:
    for variant in variants:
        key = normalized_map.get(variant)
        if key and row.get(key) not in (None, ''):
            return str(row.get(key)).strip()
    return default


def _detect_direction(amount: Decimal, raw_direction: str) -> str:
    raw = (raw_direction or '').strip().lower()

    expense_markers = {'expense', 'витрата', 'витрати', 'debit', 'card', 'списання', 'withdrawal', 'out'}
    income_markers = {'income', 'дохід', 'credit', 'надходження', 'deposit', 'in'}

    if raw in expense_markers:
        return 'expense'
    if raw in income_markers:
        return 'income'
    return 'expense' if amount < 0 else 'income'


def _normalize_expense_category(category: str | None) -> str:
    category = (category or '').strip().lower()
    valid = {code for code, _ in Expense.CATEGORY_CHOICES}
    if category in valid:
        return category

    mapping = {
        'їжа': 'food',
        'їжа та напої': 'food',
        'еда': 'food',
        'food': 'food',
        'transport': 'transport',
        'транспорт': 'transport',
        'shopping': 'shopping',
        'шопінг': 'shopping',
        'покупки': 'shopping',
        'развлечения': 'entertainment',
        'розваги': 'entertainment',
        'entertainment': 'entertainment',
        'bills': 'bills',
        'комуналка': 'bills',
        'рахунки': 'bills',
        'health': 'health',
        'здоров’я': 'health',
        'здоровье': 'health',
        'other': 'other',
        'інше': 'other',
    }
    return mapping.get(category, 'other')


def _normalize_income_category(category: str | None) -> str:
    category = (category or '').strip().lower()
    valid = {code for code, _ in Income.INCOME_CATEGORIES}
    if category in valid:
        return category

    mapping = {
        'salary': 'salary',
        'зарплата': 'salary',
        'freelance': 'freelance',
        'фриланс': 'freelance',
        'фріланс': 'freelance',
        'gift': 'gift',
        'подарунок': 'gift',
    }
    return mapping.get(category, 'other')


def safe_predict_expense_category(description: str) -> tuple[str, float]:
    try:
        return predict_category(description)
    except Exception:
        return 'other', 0.0


def parse_bank_file(uploaded_file, source_format: str = 'auto') -> list[ParsedTransaction]:
    raw_bytes = uploaded_file.read()
    try:
        text = raw_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw_bytes.decode('cp1251')

    sample = text[:2048]
    delimiter = _sniff_delimiter(sample)

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError('CSV-файл не містить заголовків колонок.')

    normalized_map = {_normalize_header(name): name for name in reader.fieldnames}
    parsed: list[ParsedTransaction] = []

    for row in reader:
        if not any((value or '').strip() for value in row.values()):
            continue

        date_value = _choose_value(
            row,
            normalized_map,
            ['датаічас', 'datetime', 'date', 'дататачас', 'датаоперації', 'transactiondate', 'operationdate', 'дата']
        )
        time_value = _choose_value(row, normalized_map, ['time', 'час', 'время'])
        amount_value = _choose_value(
            row,
            normalized_map,
            ['amount', 'sum', 'сума', 'сумма', 'amountuah', 'total', 'сумаuah']
        )
        description = _choose_value(
            row,
            normalized_map,
            ['description', 'details', 'merchant', 'comment', 'note', 'опис', 'призначення', 'назначение', 'деталі', 'counterparty']
        )
        raw_direction = _choose_value(
            row,
            normalized_map,
            ['type', 'direction', 'operationtype', 'напрям', 'тип', 'debitcredit']
        )
        raw_category = _choose_value(
            row,
            normalized_map,
            ['category', 'категорія', 'категория']
        )

        if source_format == 'monobank_like':
            if not description:
                description = _choose_value(row, normalized_map, ['description', 'details', 'mccdescription', 'merchant'])
        elif source_format == 'privatbank_like':
            if not description:
                description = _choose_value(row, normalized_map, ['назначение', 'опис', 'details', 'comment'])

        amount = _as_decimal(amount_value)
        direction = _detect_direction(amount, raw_direction)
        occurred_at = _parse_date(date_value, time_value)
        description = description or 'Імпортована операція'

        parsed.append(
            ParsedTransaction(
                occurred_at=occurred_at,
                amount=abs(amount),
                description=description[:255],
                direction=direction,
                category=raw_category or None,
                raw_source=source_format,
            )
        )

    if not parsed:
        raise ValueError('У файлі не знайдено жодної валідної операції.')

    return parsed


def _expense_already_exists(user, tx: ParsedTransaction) -> bool:
    return Expense.objects.filter(
        user=user,
        created_at__date=tx.occurred_at.date(),
        amount=tx.amount,
        description=tx.description,
    ).exists()


def _income_already_exists(user, tx: ParsedTransaction) -> bool:
    return Income.objects.filter(
        user=user,
        created_at__date=tx.occurred_at.date(),
        amount=tx.amount,
        description=tx.description,
    ).exists()


def import_transactions(user, uploaded_file, source_format: str = 'auto') -> dict:
    transactions = parse_bank_file(uploaded_file, source_format=source_format)
    result = {
        'created_expenses': 0,
        'created_incomes': 0,
        'skipped_duplicates': 0,
        'errors': [],
    }

    for tx in transactions:
        try:
            if tx.direction == 'expense':
                if _expense_already_exists(user, tx):
                    result['skipped_duplicates'] += 1
                    continue

                predicted_category, confidence = safe_predict_expense_category(tx.description)
                category = _normalize_expense_category(tx.category) if tx.category else _normalize_expense_category(predicted_category)
                is_emotional, tag = analyze_emotional_expense(tx.description, category, tx.occurred_at)

                Expense.objects.create(
                    user=user,
                    amount=tx.amount,
                    description=tx.description,
                    created_at=tx.occurred_at,
                    category=category,
                    ml_confidence=confidence,
                    is_emotional=is_emotional,
                    emotional_tag=tag,
                    notes=f'Імпортовано з {tx.raw_source}',
                )
                result['created_expenses'] += 1
            else:
                if _income_already_exists(user, tx):
                    result['skipped_duplicates'] += 1
                    continue

                Income.objects.create(
                    user=user,
                    amount=tx.amount,
                    category=_normalize_income_category(tx.category),
                    description=tx.description,
                    created_at=tx.occurred_at,
                )
                result['created_incomes'] += 1
        except Exception as exc:
            result['errors'].append(str(exc))

    return result