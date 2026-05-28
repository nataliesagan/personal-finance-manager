from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Expense, Income, CategoryBudget


class ExpenseForm(forms.ModelForm):
    category = forms.ChoiceField(
        label='Категорія',
        required=False,
        choices=[('auto', 'Автоматично')] + list(Expense.CATEGORY_CHOICES),
        initial='auto',
        help_text='Залиште “Автоматично”, щоб система сама визначила категорію за назвою або описом витрати.',
        widget=forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'})
    )

    class Meta:
        model = Expense
        fields = ['amount', 'description', 'category', 'notes']
        labels = {
            'amount': 'Сума',
            'description': 'Назва або опис витрати',
            'notes': 'Коментар',
        }
        help_texts = {
            'description': 'Наприклад: Кава, торт, сукня, таксі, аптека, комуналка, Zara, Bolt, Сільпо.',
            'notes': 'Необов’язкове поле. Можна залишити порожнім.',
        }
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'placeholder': 'Наприклад: Кава, торт, таксі, сукня, аптека',
                'autocomplete': 'off',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Наприклад: 60',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'rows': 2,
                'placeholder': 'Додаткова інформація за потреби',
            }),
        }

    def clean_category(self):
        value = self.cleaned_data.get('category') or 'auto'
        if value == 'auto':
            return 'other'
        return value


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['amount', 'category', 'description']
        labels = {
            'amount': 'Сума',
            'category': 'Категорія',
            'description': 'Опис доходу',
        }
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Наприклад: 15000',
            }),
            'category': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'description': forms.TextInput(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'placeholder': 'Опис доходу: зарплата, бонус, подарунок',
            }),
        }


class CategoryBudgetForm(forms.ModelForm):
    class Meta:
        model = CategoryBudget
        fields = ['category', 'monthly_limit']
        labels = {
            'category': 'Категорія',
            'monthly_limit': 'Місячний ліміт',
        }
        widgets = {
            'category': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'monthly_limit': forms.NumberInput(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Наприклад: 4500',
            }),
        }


class TransactionImportForm(forms.Form):
    SOURCE_FORMAT_CHOICES = [
        ('auto', 'Автовизначення'),
        ('monobank_like', 'Monobank-подібний файл'),
        ('privatbank_like', 'PrivatBank-подібний файл'),
        ('generic', 'Звичайний CSV/XLSX'),
    ]

    file = forms.FileField(
        label='Файл з транзакціями',
        help_text='Підтримуються CSV, TSV, TXT, XLSX та XLS-файли з колонками дати, суми, опису або назви операції.',
        widget=forms.ClearableFileInput(attrs={'accept': '.csv,.tsv,.txt,.xlsx,.xls'})
    )
    source_format = forms.ChoiceField(
        label='Формат імпорту',
        choices=SOURCE_FORMAT_CHOICES,
        initial='auto',
        help_text='Якщо не знаєте точний формат, залиште “Автовизначення”.'
    )


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
