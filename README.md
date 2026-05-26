# Personal Finance Manager

Веб-сервіс для управління персональними фінансами з автоматичною категоризацією витрат на основі штучного інтелекту.

## Про проєкт

Система дозволяє користувачам:
- вести облік доходів і витрат
- автоматично категоризувати витрати за допомогою ML-моделі
- налаштовувати місячні бюджети по категоріях
- переглядати аналітику та графіки на дашборді
- аналізувати емоційні (імпульсивні) витрати
- імпортувати та експортувати дані у форматі CSV

## Технологічний стек

- **Backend:** Python 3.10+, Django 4.x
- **ML:** scikit-learn, TF-IDF, Logistic Regression
- **Frontend:** Tailwind CSS, HTMX, Chart.js
- **База даних:** SQLite

## Вимоги

- Python 3.10+
- pip

## Встановлення та запуск

### 1. Клонувати репозиторій
```bash
git clone https://github.com/nataliesagan/personal-finance-manager
cd personal-finance-manager/Projects
```

### 2. Встановити залежності
```bash
pip install -r requirements.txt
```

### 3. Виконати міграції
```bash
python manage.py migrate
```

### 4. Наповнити базу тестовими даними
```bash
python manage.py seed_test_data
```

### 5. Запустити сервер
```bash
python manage.py runserver
```

### 6. Відкрити у браузері
```
http://127.0.0.1:8000
```

## Запуск тестів

```bash
python manage.py test
```

## Навчання ML-моделі

```bash
python expenses/ml/train_classifier.py
```

## Донавчання моделі на основі фідбеку користувача

```bash
python expenses/ml/train_from_feedback.py
```

## Структура проєкту

```
Projects/
├── expenses/                         # Основний додаток
│   ├── management/
│   │   └── commands/
│   │       ├── seed_demo_data.py     # Демо-дані
│   │       └── seed_test_data.py     # Тестові дані
│   ├── migrations/                   # Міграції БД
│   ├── ml/
│   │   ├── data/
│   │   │   └── expenses_train.csv    # Навчальний датасет
│   │   ├── models/
│   │   │   └── expense_classifier.joblib  # Збережена ML-модель
│   │   ├── expense_classifier.py     # Завантаження моделі та predict_category()
│   │   ├── train_classifier.py       # Навчання моделі
│   │   └── train_from_feedback.py    # Донавчання на фідбеку
│   ├── services/
│   │   ├── bank_io.py                # Імпорт/експорт CSV (Monobank, PrivatBank)
│   │   └── emotional_advice.py       # Поради щодо емоційних витрат
│   ├── templates/expenses/
│   │   ├── partials/
│   │   │   ├── _expense_form.html    # HTMX-форма витрати
│   │   │   └── _expense_table.html   # HTMX-таблиця витрат
│   │   ├── base.html                 # Базовий шаблон
│   │   ├── dashboard.html            # Дашборд
│   │   ├── budget_list.html          # Бюджети
│   │   ├── emotional_report.html     # Емоційні витрати
│   │   ├── expense_list.html         # Список витрат
│   │   ├── expense_edit.html         # Редагування витрати
│   │   ├── expense_form.html         # Форма витрати
│   │   ├── income_list.html          # Список доходів
│   │   └── transaction_import.html   # Імпорт транзакцій
│   │   └── registration/
│   │       ├── login.html
│   │       └── signup.html
│   ├── admin.py
│   ├── apps.py
│   ├── emotion_rules.py              # Правила виявлення емоційних витрат
│   ├── forms.py                      # Django-форми
│   ├── models.py                     # Expense, Income, CategoryBudget, CategoryFeedback
│   ├── tests.py                      # Тести
│   ├── urls.py                       # Маршрути
│   └── views.py                      # Представлення
├── finance_manager/                  # Конфігурація проєкту
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── db.sqlite3                        # База даних
└── manage.py
```

## Маршрути

| URL | Опис |
|-----|------|
| `/` | Головний дашборд |
| `/expenses/` | Список витрат |
| `/incomes/` | Список доходів |
| `/budgets/` | Управління бюджетами |
| `/emotional/` | Аналіз емоційних витрат |
| `/transactions/import/` | Імпорт CSV |
| `/transactions/export/` | Експорт CSV |

## Автор

Саган Наталія Костянтинівна  
