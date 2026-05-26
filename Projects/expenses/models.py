from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Їжа та напої'),
        ('transport', 'Транспорт'),
        ('shopping', 'Шопінг'),
        ('entertainment', 'Розваги'),
        ('bills', 'Комуналка/рахунки'),
        ('health', 'Здоровʼя'),
        ('other', 'Інше'),
    ]

    EMOTIONAL_TAG_CHOICES = [
        ('fast_food', 'Фастфуд / імпульсивна їжа'),
        ('online_shopping', 'Онлайн-шопінг'),
        ('late_night', 'Пізні витрати'),
        ('entertainment', 'Розваги'),
        ('none', 'Не емоційна витрата'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default='other')
    ml_confidence = models.FloatField(default=0.0)

    is_emotional = models.BooleanField(default=False)
    emotional_tag = models.CharField(
        max_length=32,
        choices=EMOTIONAL_TAG_CHOICES,
        default='none'
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.description} ({self.amount} грн)'


class CategoryFeedback(models.Model):
    expense = models.OneToOneField(Expense, on_delete=models.CASCADE, related_name='feedback')
    original_category = models.CharField(max_length=32, choices=Expense.CATEGORY_CHOICES)
    corrected_category = models.CharField(max_length=32, choices=Expense.CATEGORY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Feedback for expense {self.expense_id}'


class Income(models.Model):
    INCOME_CATEGORIES = [
        ('salary', 'Зарплата'),
        ('freelance', 'Фріланс'),
        ('gift', 'Подарунки'),
        ('other', 'Інше'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=32, choices=INCOME_CATEGORIES)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Доход {self.amount} ({self.get_category_display()})'


class CategoryBudget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.CharField(max_length=32, choices=Expense.CATEGORY_CHOICES)
    monthly_limit = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('user', 'category')

    def __str__(self):
        return f'Бюджет {self.user.username} – {self.get_category_display()}'
