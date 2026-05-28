# Finance Manager

Finance Manager is a Django web application for tracking incomes, expenses, budgets, imported bank transactions, automatic expense categorisation and emotional spending analytics.

## Main features

- User registration and login.
- Manual expense and income tracking.
- Automatic expense categorisation by transaction name or description.
- Stable keyword fallback for simple cases such as `Кава`, `торт`, `сукня`, `таксі`, `аптека`, `комуналка`.
- Emotional spending detection for coffee, desserts, fast food, online shopping, entertainment and late-night purchases.
- Humorous recommendations based on emotional spending patterns.
- CSV, TSV, TXT, XLSX and XLS transaction import.
- CSV export of user data.
- Dashboard charts for categories, expenses by day and cash flow.
- Monthly category budgets.
- Automated tests for categorisation, emotional spending and imports.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
```

On macOS or Linux use:

```bash
source .venv/bin/activate
```

## Run the project

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Create demo data

Create a user in the interface or through Django admin, then run:

```bash
python manage.py seed_demo_data username --replace
```

There is also a ready command for a test user:

```bash
python manage.py seed_test_data
```

Test login after `seed_test_data`:

```text
login: rostik
password: 123456
```

## Run tests

```bash
python manage.py test expenses
```

The tests verify that:

- `Кава` is categorised as food and emotional spending.
- `торт` is categorised as food.
- `сукня` is categorised as shopping.
- `таксі` is categorised as transport.
- `аптека` is categorised as health.
- CSV and XLSX import create correct expenses.
- Manual expense creation with category `Автоматично` works correctly.

## Import format

Supported file extensions:

```text
.csv, .tsv, .txt, .xlsx, .xls
```

Minimal columns:

```text
date, amount, description
```

Recommended columns:

```text
date, amount, description, type, category
```

Example CSV:

```csv
date;amount;description;type
2026-05-27 17:44;-60;Кава;expense
2026-05-27 18:20;-350;Сукня;expense
2026-05-27 19:10;15000;Зарплата;income
```

The importer also recognises Ukrainian and Russian column names such as `дата`, `сума`, `опис`, `призначення`, `тип`, `категорія`.

## How automatic categorisation works

The categorisation system uses two layers:

1. Deterministic keyword rules for common user and bank descriptions.
2. Optional ML model fallback for less obvious descriptions.

The rule-based layer prevents critical failures when the ML model is missing, outdated or uncertain.

Examples:

| Text | Category |
|---|---|
| Кава | Їжа та напої |
| торт | Їжа та напої |
| піца | Їжа та напої |
| сукня | Шопінг |
| одяг | Шопінг |
| таксі | Транспорт |
| аптека | Здоровʼя |
| комуналка | Комуналка/рахунки |

## How emotional spending works

Emotional expenses are detected using:

- transaction name or description,
- expense category,
- transaction time.

Examples of emotional spending markers:

- coffee, cafe, cake, dessert, pizza, sushi,
- fast food,
- online shopping,
- entertainment,
- late-night food or shopping.

The project shows emotional spending separately and generates short recommendations.
