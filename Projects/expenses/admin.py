from django.contrib import admin
from .models import Expense, CategoryFeedback, Income, CategoryBudget


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'category', 'ml_confidence',
                    'is_emotional', 'emotional_tag', 'created_at')
    list_filter = ('category', 'is_emotional', 'emotional_tag', 'created_at')
    search_fields = ('description', 'notes')


@admin.register(CategoryFeedback)
class CategoryFeedbackAdmin(admin.ModelAdmin):
    list_display = ('expense', 'original_category', 'corrected_category', 'created_at')
    list_filter = ('original_category', 'corrected_category', 'created_at')


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'category', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('description',)


@admin.register(CategoryBudget)
class CategoryBudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'monthly_limit')
    list_filter = ('category',)
