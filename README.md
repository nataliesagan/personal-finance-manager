# Personal Finance Manager

Веб-сервіс для управління персональними фінансами з автоматичною 
категоризацією витрат на основі штучного інтелекту.

---

## Автор

- **ПІБ**: Саган Наталія Костянтинівна
- **Група**: ФеС-42
- **Керівник**: Шувар Роман Ярославович, доц.
- **Дата виконання**: 2026

---

## Загальна інформація

- **Тип проєкту**: Веб-застосунок
- **Мова програмування**: Python
- **Фреймворки / Бібліотеки**: Django, scikit-learn, HTMX, Tailwind CSS, Chart.js

---

## Опис функціоналу

- Реєстрація та авторизація користувачів
- Облік витрат і доходів з категоріями
- Автоматична категоризація витрат за допомогою ML (TF-IDF + Logistic Regression)
- Дашборд з аналітикою та графіками
- Аналіз емоційних (імпульсивних) витрат
- Імпорт/експорт даних у форматі CSV (Monobank, PrivatBank)
- Налаштування місячних бюджетів по категоріях

---

## Опис основних файлів

| Файл | Призначення |
|------|-------------|
| `expenses/models.py` | Моделі: Expense, Income, CategoryBudget, CategoryFeedback |
| `expenses/views.py` | Представлення: дашборд, списки, форми |
| `expenses/urls.py` | Маршрути додатку |
| `expenses/forms.py` | Django-форми |
| `expenses/emotion_rules.py` | Правила виявлення емоційних витрат |
| `expenses/ml/train_classifier.py` | Навчання ML-моделі |
| `expenses/ml/expense_classifier.py` | Завантаження моделі та predict_category() |
| `expenses/ml/train_from_feedback.py` | Донавчання на основі фідбеку |
| `expenses/services/bank_io.py` | Імпорт/експорт CSV |
| `finance_manager/settings.py` | Налаштування проєкту |

---

## Як запустити проєкт

### 1. Встановлення інструментів

- Python 3.10+

### 2. Клонування репозиторію

```bash
git clone https://github.com/nataliesagan/personal-finance-manager
cd personal-finance-manager/Projects
```

### 3. Встановлення залежностей

```bash
pip install -r requirements.txt
```

### 4. Міграції бази даних

```bash
python manage.py migrate
```

### 5. Наповнення тестовими даними

```bash
python manage.py seed_test_data
```

### 6. Запуск сервера

```bash
python manage.py runserver
```

### 7. Відкрити у браузері

```
http://127.0.0.1:8000
```

---

## Запуск тестів

```bash
python manage.py test
```

---

## Навчання ML-моделі

```bash
python expenses/ml/train_classifier.py
```

## Донавчання на основі фідбеку користувача

```bash
python expenses/ml/train_from_feedback.py
```

---

## Маршрути Django

| URL | Опис |
|-----|------|
| `/` | Головний дашборд |
| `/expenses/` | Список витрат |
| `/incomes/` | Список доходів |
| `/budgets/` | Управління бюджетами |
| `/emotional/` | Аналіз емоційних витрат |
| `/transactions/import/` | Імпорт CSV |
| `/transactions/export/` | Експорт CSV |

---

## Інструкція для користувача

1. **Головна сторінка (дашборд)** — загальна аналітика, графіки витрат по категоріях, стан бюджетів
2. **Витрати** — додавання, редагування, видалення витрат; ML автоматично визначає категорію
3. **Доходи** — облік доходів по категоріях
4. **Бюджети** — встановлення місячного ліміту по кожній категорії
5. **Емоційні витрати** — аналіз імпульсивних покупок за ключовими словами
6. **Імпорт CSV** — завантаження виписки з Monobank або PrivatBank

---

## Скріншоти

![Screenshot 1](screenshots/Screenshot%20(2).png)
![Screenshot 2](screenshots/Screenshot%20(3).png)
![Screenshot 3](screenshots/Screenshot%20(4).png)
![Screenshot 4](screenshots/Screenshot%20(5).png)

---

## Проблеми і рішення

| Проблема | Рішення |
|----------|---------|
| Модель не завантажується | Запустіть `train_classifier.py` для створення `.joblib` файлу |
| Помилка міграцій | Видаліть `db.sqlite3` і запустіть `migrate` знову |
| CSV не імпортується | Перевірте формат файлу — підтримується Monobank, PrivatBank, стандарт |

---

## Releases

Версія `v1.0` доступна за посиланням:
https://github.com/nataliesagan/personal-finance-manager/releases/tag/v1.0

---

## Використані джерела

- [Django документація](https://docs.djangoproject.com/)
- [scikit-learn документація](https://scikit-learn.org/)
- [HTMX документація](https://htmx.org/)
- [Tailwind CSS документація](https://tailwindcss.com/)
- [Chart.js документація](https://www.chartjs.org/)
```
