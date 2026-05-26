from decimal import Decimal
from datetime import timedelta
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from expenses.models import Expense, Income, CategoryBudget
from expenses.emotion_rules import analyze_emotional_expense


class Command(BaseCommand):
    help = "Заполняет выбранного пользователя тестовыми доходами, расходами и бюджетами."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Username пользователя")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Удалить старые расходы/доходы/бюджеты пользователя перед заполнением",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"]
        replace = options["replace"]

        User = get_user_model()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Пользователь "{username}" не найден')

        if replace:
            Expense.objects.filter(user=user).delete()
            Income.objects.filter(user=user).delete()
            CategoryBudget.objects.filter(user=user).delete()
            self.stdout.write(self.style.WARNING("Старые данные пользователя удалены."))

        self._create_budgets(user)
        self._create_incomes(user)
        self._create_expenses(user)

        self.stdout.write(self.style.SUCCESS(
            f'Тестовые данные успешно созданы для пользователя "{username}".'
        ))

    def _create_budgets(self, user):
        budgets = {
            "food": Decimal("4500.00"),
            "transport": Decimal("1800.00"),
            "shopping": Decimal("3500.00"),
            "entertainment": Decimal("2200.00"),
            "bills": Decimal("3000.00"),
            "health": Decimal("1500.00"),
            "other": Decimal("1200.00"),
        }

        for category, limit in budgets.items():
            CategoryBudget.objects.update_or_create(
                user=user,
                category=category,
                defaults={"monthly_limit": limit},
            )

    def _create_incomes(self, user):
        now = timezone.now()

        incomes = [
            {
                "amount": Decimal("28500.00"),
                "category": "salary",
                "description": "Зарплата за місяць",
                "created_at": now - timedelta(days=18),
            },
            {
                "amount": Decimal("4200.00"),
                "category": "freelance",
                "description": "Фріланс-проєкт",
                "created_at": now - timedelta(days=9),
            },
            {
                "amount": Decimal("1500.00"),
                "category": "gift",
                "description": "Подарунок від родини",
                "created_at": now - timedelta(days=3),
            },
        ]

        for item in incomes:
            Income.objects.create(
                user=user,
                amount=item["amount"],
                category=item["category"],
                description=item["description"],
                created_at=item["created_at"],
            )

    def _create_expenses(self, user):
        now = timezone.now()

        expense_templates = [
            ("food", Decimal("185.00"), "Продукти в АТБ", "Базові покупки"),
            ("food", Decimal("129.00"), "Coffee late evening", "Хотілося кави після важкого дня"),
            ("food", Decimal("249.00"), "McDonalds combo", "Швидкий перекус"),
            ("transport", Decimal("220.00"), "Таксі по місту", "Запізнювалась"),
            ("transport", Decimal("30.00"), "Маршрутка", ""),
            ("shopping", Decimal("899.00"), "Замовлення на Rozetka", "Купила дрібниці онлайн"),
            ("shopping", Decimal("1450.00"), "Кросівки", "Наче треба було, але не факт"),
            ("shopping", Decimal("399.00"), "Steam game", "Імпульсивна покупка"),
            ("entertainment", Decimal("320.00"), "Cinema with friends", "Похід у кіно"),
            ("entertainment", Decimal("410.00"), "Bar evening", "Трохи відпочинку"),
            ("bills", Decimal("1350.00"), "Комунальні послуги", ""),
            ("bills", Decimal("289.00"), "Інтернет", ""),
            ("health", Decimal("260.00"), "Аптека", "Ліки"),
            ("other", Decimal("175.00"), "Подарункова упаковка", ""),
            ("food", Decimal("315.00"), "Pizza night", "Замовлення ввечері"),
            ("food", Decimal("97.00"), "Starbucks coffee", "Кава по дорозі"),
            ("shopping", Decimal("780.00"), "AliExpress order", "Онлайн-шопінг"),
            ("entertainment", Decimal("199.00"), "Spotify subscription", ""),
            ("transport", Decimal("410.00"), "Таксі після 22:00", "Пізня поїздка"),
            ("other", Decimal("120.00"), "Канцтовари", ""),
        ]

        random.seed(42)

        for index, (category, amount, description, notes) in enumerate(expense_templates):
            day_shift = random.randint(0, 27)
            hour = random.choice([9, 11, 13, 16, 19, 21, 22, 23])
            minute = random.choice([0, 10, 15, 20, 30, 40, 50])

            created_at = now - timedelta(days=day_shift)
            created_at = created_at.replace(hour=hour, minute=minute, second=0, microsecond=0)

            is_emotional, tag = analyze_emotional_expense(description, category, created_at)

            ml_confidence = 0.93 if category in ("food", "shopping", "entertainment") else 0.78

            Expense.objects.create(
                user=user,
                amount=amount,
                description=description,
                created_at=created_at,
                category=category,
                ml_confidence=ml_confidence,
                is_emotional=is_emotional,
                emotional_tag=tag,
                notes=notes,
            )