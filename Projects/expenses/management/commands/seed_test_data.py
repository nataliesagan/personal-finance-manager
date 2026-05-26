from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from expenses.models import Expense, Income, CategoryBudget
from expenses.ml.expense_classifier import predict_category
from expenses.emotion_rules import analyze_emotional_expense


class Command(BaseCommand):
    help = "Створює тестові дані: користувача, доходи, витрати, бюджети."

    def handle(self, *args, **options):
        # 1. Користувач
        user, created = User.objects.get_or_create(
            username="rostik",
            defaults={"email": "popa@gmail.com"}
        )
        if created:
            user.set_password("123456")
            user.save()
            self.stdout.write(self.style.SUCCESS(
                "Створено тестового користувача: логін=rostik, пароль=123456"
            ))
        else:
            self.stdout.write("Користувач 'rostik' вже існує.")

        if Expense.objects.filter(user=user).exists() or Income.objects.filter(user=user).exists():
            self.stdout.write(self.style.WARNING(
                "У користувача вже є витрати/доходи. Нові дані будуть додані поверх існуючих."
            ))

        now = timezone.now()

        # 2. Доходи (усі в поточному місяці)
        income_templates = [
            ("Зарплата основна", 25000, "salary"),
            ("Фріланс проект", 8000, "freelance"),
            ("Подарунок на День народження", 3000, "gift"),
            ("Повернення боргу", 2000, "other"),
        ]

        for desc, amount, cat in income_templates:
            # случайный день внутри текущего месяца (последние 20 дней)
            created_at = now - timedelta(days=random.randint(0, 19))
            Income.objects.create(
                user=user,
                amount=amount,
                category=cat,
                description=desc,
                created_at=created_at,
            )

        self.stdout.write(self.style.SUCCESS("Створено тестові доходи."))

        # 3. Витрати: TRUE-категорія + ML-категорія (як демонстрація)
        #   third элемент — "правильная" категория, которая гарантированно попадает в бюджеты
        expense_templates = [
            ("McDonalds lunch", 220, "food"),
            ("KFC late dinner", 260, "food"),
            ("Supermarket groceries", 850, "food"),
            ("Pizza Hut delivery", 300, "food"),
            ("Кава Starbucks", 120, "food"),

            ("Uber to university", 95, "transport"),
            ("Metro ticket", 40, "transport"),
            ("Taxi at night", 180, "transport"),

            ("Rozetka electronics order", 3200, "shopping"),
            ("AliExpress gadgets", 900, "shopping"),
            ("New sneakers Nike", 2700, "shopping"),

            ("Cinema tickets", 280, "entertainment"),
            ("Netflix monthly subscription", 250, "entertainment"),
            ("Steam games sale", 600, "entertainment"),
            ("Bar with friends", 450, "entertainment"),

            ("Electricity bill", 1100, "bills"),
            ("Gas bill", 900, "bills"),
            ("Water bill", 300, "bills"),

            ("Pharmacy vitamins", 350, "health"),
            ("Doctor visit", 800, "health"),

            ("Random purchase", 150, "other"),
        ]

        from expenses.models import Expense as ExpenseModel
        valid_categories = {c[0] for c in ExpenseModel.CATEGORY_CHOICES}

        for desc, base_amount, true_cat in expense_templates:
            # сумма чуть варьируется
            amount = base_amount + random.randint(-50, 50)

            # гарантируем, что дата в поточному місяці (останні 25 днів)
            created_at = now - timedelta(days=random.randint(0, 24))
            hour = random.choice([11, 13, 17, 20, 22])
            created_at = created_at.replace(
                hour=hour, minute=random.randint(0, 59),
                second=0, microsecond=0
            )

            # пробуем ML-категоризацию (для демо), но не даём ей "сломать" правильную категорию
            ml_cat, conf = predict_category(desc)
            if ml_cat not in valid_categories:
                # если модель вернула что-то странное — берём true_cat и считаем уверенность 1.0
                ml_cat = true_cat
                conf = 1.0

            # эмоциональний аналіз
            is_emotional, tag = analyze_emotional_expense(desc, ml_cat, created_at)

            Expense.objects.create(
                user=user,
                amount=amount,
                description=desc,
                created_at=created_at,
                category=ml_cat,       # в БД хранится то, что "решила" модель (или true_cat как fallback)
                ml_confidence=conf,
                is_emotional=is_emotional,
                emotional_tag=tag,
                notes="test data",
            )

        self.stdout.write(self.style.SUCCESS("Створено тестові витрати."))

        # 5. Бюджети по категоріях
        CategoryBudget.objects.get_or_create(
            user=user, category="food",
            defaults={"monthly_limit": 4000}
        )
        CategoryBudget.objects.get_or_create(
            user=user, category="transport",
            defaults={"monthly_limit": 1500}
        )
        CategoryBudget.objects.get_or_create(
            user=user, category="shopping",
            defaults={"monthly_limit": 5000}
        )
        CategoryBudget.objects.get_or_create(
            user=user, category="entertainment",
            defaults={"monthly_limit": 3000}
        )
        CategoryBudget.objects.get_or_create(
            user=user, category="bills",
            defaults={"monthly_limit": 4500}
        )
        CategoryBudget.objects.get_or_create(
            user=user, category="health",
            defaults={"monthly_limit": 2000}
        )

        self.stdout.write(self.style.SUCCESS("Створено тестові бюджети."))
        self.stdout.write(self.style.SUCCESS("Готово! Перевірте дашборд та інші сторінки."))

