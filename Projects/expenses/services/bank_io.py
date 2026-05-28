from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils import timezone

from ..emotion_rules import analyze_emotional_expense
from ..models import Expense, Income
from ..ml.expense_classifier import predict_category
from .category_engine import normalize_category, normalize_text

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
    '%d-%m-%Y %H:%M:%S',
    '%d-%m-%Y %H:%M',
    '%d-%m-%Y',
]

DATE_COLUMNS = [
    'дата і час', 'датаічас', 'datetime', 'date', 'дата та час', 'дататачас',
    'дата операції', 'датаоперації', 'transaction date', 'transactiondate',
    'operation date', 'operationdate', 'дата', 'date time', 'datetimeutc',
]

TIME_COLUMNS = ['time', 'час', 'время', 'час операції', 'часоперації']

AMOUNT_COLUMNS = [
    'amount', 'sum', 'сума', 'сумма', 'amount uah', 'amountuah', 'total',
    'сума uah', 'сумаuah', 'сума операції', 'сумаоперації',
    'сума у валюті картки', 'сумаувалютікартки', 'сума в валюті картки', 'сумаввалютікартки',
    'card amount', 'cardamount', 'transaction amount', 'transactionamount',
]

EXPENSE_AMOUNT_COLUMNS = [
    'витрата', 'витрати', 'expense', 'expenses', 'debit', 'списання',
    'сума списання', 'сумасписання', 'withdrawal', 'outcome', 'out',
]

INCOME_AMOUNT_COLUMNS = [
    'дохід', 'доход', 'income', 'incomes', 'credit', 'надходження', 'поповнення',
    'сума поповнення', 'сумапоповнення', 'deposit', 'in',
]

DESCRIPTION_COLUMNS = [
    'description', 'details', 'merchant', 'merchant name', 'merchantname',
    'comment', 'note', 'опис', 'опис операції', 'описоперації', 'призначення',
    'призначення платежу', 'призначенняплатежу', 'назначение', 'деталі',
    'деталі операції', 'деталіоперації', 'counterparty', 'контрагент',
    'назва', 'назва операції', 'назваоперації', 'операція', 'операция',
    'місце операції', 'місцеоперації', 'место операции', 'местооперации',
    'mcc description', 'mccdescription', 'mcc', 'payee', 'receiver', 'sender',
]

DIRECTION_COLUMNS = [
    'type', 'direction', 'operation type', 'operationtype', 'напрям', 'тип',
    'тип операції', 'типоперації', 'debit credit', 'debitcredit', 'вид операції',
    'видоперації', 'income expense', 'incomeexpense',
]

CATEGORY_COLUMNS = [
    'category', 'категорія', 'категория', 'mcc category', 'mcccategory', 'група', 'group',
]

EXPENSE_MARKERS = {
    'expense', 'expenses', 'витрата', 'витрати', 'debit', 'card', 'списання',
    'withdrawal', 'out', 'outcome', 'покупка', 'оплата', 'оплата карткою', 'payment',
}

INCOME_MARKERS = {
    'income', 'incomes', 'дохід', 'доход', 'credit', 'надходження', 'поступление',
    'deposit', 'in', 'поповнення', 'зарахування', 'salary', 'зарплата',
}

@dataclass
class ParsedTransaction:
    occurred_at: datetime
    amount: Decimal
    description: str
    direction: str
    category: str | None
    raw_source: str
    row_number: int | None = None

@dataclass
class ImportStats:
    created_expenses: int = 0
    created_incomes: int = 0
    skipped_duplicates: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            'created_expenses': self.created_expenses,
            'created_incomes': self.created_incomes,
            'skipped_duplicates': self.skipped_duplicates,
            'errors': self.errors,
        }


def _normalize_header(value: object) -> str:
    return ''.join(ch for ch in normalize_text(value) if ch.isalnum())


def _sniff_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
        return dialect.delimiter
    except csv.Error:
        tab_count = sample.count('\t')
        semicolon_count = sample.count(';')
        comma_count = sample.count(',')
        if tab_count >= semicolon_count and tab_count >= comma_count:
            return '\t'
        if semicolon_count >= comma_count:
            return ';'
        return ','


def _clean_amount(value: object) -> str:
    cleaned = str(value or '').strip()
    cleaned = cleaned.replace('\xa0', '').replace(' ', '')
    cleaned = cleaned.replace('грн', '').replace('uah', '').replace('UAH', '')
    cleaned = cleaned.replace('₴', '').replace('$', '').replace('€', '')
    cleaned = cleaned.replace(',', '.')

    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]

    return cleaned


def _as_decimal(value: object) -> Decimal:
    cleaned = _clean_amount(value)
    if not cleaned:
        raise InvalidOperation('empty amount')
    return Decimal(cleaned)


def _make_aware(dt: datetime) -> datetime:
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _parse_date(date_value: object, time_value: object = '') -> datetime:
    if isinstance(date_value, datetime):
        return _make_aware(date_value)

    if isinstance(date_value, date):
        return _make_aware(datetime.combine(date_value, datetime.min.time()))

    if hasattr(date_value, 'to_pydatetime'):
        return _make_aware(date_value.to_pydatetime())

    date_text = str(date_value or '').strip()
    time_text = str(time_value or '').strip()

    if not date_text:
        raise ValueError('Дата операції порожня.')

    combined = f'{date_text} {time_text}'.strip()

    for candidate in [combined, date_text]:
        if not candidate:
            continue
        for fmt in DATE_FORMATS:
            try:
                return _make_aware(datetime.strptime(candidate, fmt))
            except ValueError:
                continue

    raise ValueError(f'Неможливо розпізнати дату: {combined or date_text}')


def _choose_value(row: dict, normalized_map: dict[str, str], variants: list[str], default: object = '') -> object:
    for variant in variants:
        key = normalized_map.get(_normalize_header(variant))
        if key is None:
            continue
        value = row.get(key)
        if value is None:
            continue
        if str(value).strip() != '':
            return value
    return default


def _detect_direction(amount: Decimal, raw_direction: object) -> str:
    raw = normalize_text(raw_direction)
    if raw in EXPENSE_MARKERS:
        return 'expense'
    if raw in INCOME_MARKERS:
        return 'income'
    return 'expense' if amount < 0 else 'income'


def _read_csv_rows(raw_bytes: bytes) -> tuple[list[str], list[dict]]:
    last_error: Exception | None = None
    for encoding in ['utf-8-sig', 'utf-8', 'cp1251', 'windows-1251']:
        try:
            text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    else:
        raise ValueError(f'Не вдалося прочитати файл. Помилка кодування: {last_error}')

    sample = text[:4096]
    delimiter = _sniff_delimiter(sample)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    if not reader.fieldnames:
        raise ValueError('CSV/TSV-файл не містить заголовків колонок.')

    return reader.fieldnames, list(reader)


def _read_excel_rows(raw_bytes: bytes) -> tuple[list[str], list[dict]]:
    try:
        import pandas as pd
    except Exception as exc:
        raise ImportError(
            'Для імпорту XLSX/XLS потрібно встановити pandas та openpyxl: pip install pandas openpyxl'
        ) from exc

    df = pd.read_excel(io.BytesIO(raw_bytes), dtype=str, keep_default_na=False)
    if df.empty:
        raise ValueError('Excel-файл не містить операцій.')
    fieldnames = list(df.columns)
    if not fieldnames:
        raise ValueError('Excel-файл не містить заголовків колонок.')
    return fieldnames, df.to_dict(orient='records')


def _make_description(row: dict, normalized_map: dict[str, str]) -> str:
    primary = _choose_value(row, normalized_map, DESCRIPTION_COLUMNS, '')
    if primary:
        return str(primary).strip()

    fallback_parts = []
    for key in normalized_map.values():
        text = str(row.get(key) or '').strip()
        if text and len(text) <= 80:
            fallback_parts.append(text)
        if len(fallback_parts) >= 3:
            break
    return ' / '.join(fallback_parts) if fallback_parts else 'Імпортована операція'


def _parse_rows(fieldnames: list[str], rows: list[dict], source_format: str) -> tuple[list[ParsedTransaction], list[str]]:
    normalized_map = {_normalize_header(name): name for name in fieldnames}
    parsed: list[ParsedTransaction] = []
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        if not any(str(value or '').strip() for value in row.values()):
            continue

        try:
            date_value = _choose_value(row, normalized_map, DATE_COLUMNS)
            time_value = _choose_value(row, normalized_map, TIME_COLUMNS)

            amount_value = _choose_value(row, normalized_map, AMOUNT_COLUMNS)
            expense_amount_value = _choose_value(row, normalized_map, EXPENSE_AMOUNT_COLUMNS)
            income_amount_value = _choose_value(row, normalized_map, INCOME_AMOUNT_COLUMNS)

            raw_direction = _choose_value(row, normalized_map, DIRECTION_COLUMNS)

            if not amount_value:
                if expense_amount_value:
                    amount_value = expense_amount_value
                    raw_direction = raw_direction or 'expense'
                elif income_amount_value:
                    amount_value = income_amount_value
                    raw_direction = raw_direction or 'income'

            if not amount_value:
                raise ValueError('не знайдено суму операції')

            amount = _as_decimal(amount_value)
            direction = _detect_direction(amount, raw_direction)
            occurred_at = _parse_date(date_value, time_value)
            description = _make_description(row, normalized_map)[:255]
            raw_category = _choose_value(row, normalized_map, CATEGORY_COLUMNS, '')

            parsed.append(ParsedTransaction(
                occurred_at=occurred_at,
                amount=abs(amount),
                description=description,
                direction=direction,
                category=str(raw_category).strip() if raw_category else None,
                raw_source=source_format,
                row_number=index,
            ))
        except Exception as exc:
            errors.append(f'Рядок {index}: {exc}')

    if not parsed and errors:
        raise ValueError('Не вдалося імпортувати жодної операції. ' + '; '.join(errors[:3]))
    if not parsed:
        raise ValueError('У файлі не знайдено жодної валідної операції.')

    return parsed, errors


def parse_bank_file(uploaded_file, source_format: str = 'auto') -> list[ParsedTransaction]:
    raw_bytes = uploaded_file.read()
    filename = (getattr(uploaded_file, 'name', '') or '').lower()

    if filename.endswith(('.xlsx', '.xls')):
        fieldnames, rows = _read_excel_rows(raw_bytes)
    else:
        fieldnames, rows = _read_csv_rows(raw_bytes)

    parsed, _errors = _parse_rows(fieldnames, rows, source_format)
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


def safe_predict_expense_category(description: str) -> tuple[str, float]:
    try:
        return predict_category(description)
    except Exception:
        return 'other', 0.0


def import_transactions(user, uploaded_file, source_format: str = 'auto') -> dict:
    raw_bytes = uploaded_file.read()
    filename = (getattr(uploaded_file, 'name', '') or '').lower()

    if filename.endswith(('.xlsx', '.xls')):
        fieldnames, rows = _read_excel_rows(raw_bytes)
    else:
        fieldnames, rows = _read_csv_rows(raw_bytes)

    transactions, parse_errors = _parse_rows(fieldnames, rows, source_format)
    result = ImportStats(errors=parse_errors[:20])

    for tx in transactions:
        try:
            if tx.direction == 'expense':
                if _expense_already_exists(user, tx):
                    result.skipped_duplicates += 1
                    continue

                predicted_category, confidence = safe_predict_expense_category(tx.description)
                raw_category = normalize_category(tx.category) if tx.category else 'other'
                category = raw_category if raw_category != 'other' else normalize_category(predicted_category)
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
                    notes=f'Імпортовано з {tx.raw_source}. Рядок файлу: {tx.row_number or "невідомо"}.',
                )
                result.created_expenses += 1
            else:
                if _income_already_exists(user, tx):
                    result.skipped_duplicates += 1
                    continue

                Income.objects.create(
                    user=user,
                    amount=tx.amount,
                    category='other',
                    description=tx.description,
                    created_at=tx.occurred_at,
                )
                result.created_incomes += 1
        except Exception as exc:
            result.errors.append(f'Рядок {tx.row_number or "?"}: {exc}')

    return result.as_dict()
