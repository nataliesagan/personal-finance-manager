from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .emotion_rules import analyze_emotional_expense, analyze_emotional_expense_details
from .models import Expense
from .ml.expense_classifier import predict_category, predict_category_detailed
from .services.bank_io import import_transactions, parse_bank_file


class CategoryPredictionTests(TestCase):
    def assertCategory(self, text, expected):
        category, confidence = predict_category(text)
        self.assertEqual(category, expected)
        self.assertGreater(confidence, 0)

    def test_basic_user_words_are_categorized(self):
        cases = {
            'Кава': 'food',
            'торт': 'food',
            'піца': 'food',
            'сукня': 'shopping',
            'одяг': 'shopping',
            'таксі': 'transport',
            'аптека': 'health',
            'комуналка': 'bills',
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertCategory(text, expected)

    def test_merchant_names_are_categorized(self):
        cases = {
            'Zara сукня': 'shopping',
            'Bolt поїздка': 'transport',
            'Сільпо продукти': 'food',
            'Rozetka замовлення': 'shopping',
            'Netflix subscription': 'entertainment',
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertCategory(text, expected)

    def test_detailed_decision_contains_explanation(self):
        decision = predict_category_detailed('Кава')
        self.assertEqual(decision.category, 'food')
        self.assertIn('ключов', decision.explanation.lower())


class EmotionalExpenseTests(TestCase):
    def test_coffee_is_emotional_fast_food(self):
        dt = timezone.make_aware(datetime(2026, 5, 27, 17, 44))
        is_emotional, tag = analyze_emotional_expense('Кава', 'food', dt)
        self.assertTrue(is_emotional)
        self.assertEqual(tag, 'fast_food')

    def test_cake_is_emotional_fast_food(self):
        dt = timezone.make_aware(datetime(2026, 5, 27, 14, 30))
        decision = analyze_emotional_expense_details('торт', 'food', dt)
        self.assertTrue(decision.is_emotional)
        self.assertEqual(decision.tag, 'fast_food')
        self.assertIn('торт', decision.reason)

    def test_toy_is_not_emotional_by_default(self):
        dt = timezone.make_aware(datetime(2026, 5, 27, 14, 30))
        is_emotional, tag = analyze_emotional_expense('іграшки', 'shopping', dt)
        self.assertFalse(is_emotional)
        self.assertEqual(tag, 'none')


class ImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password123')

    def test_csv_import_creates_expense_with_auto_category_and_emotion(self):
        csv_content = 'date;amount;description;type\n2026-05-27 17:44;-60;Кава;expense\n'.encode('utf-8-sig')
        uploaded_file = SimpleUploadedFile('transactions.csv', csv_content, content_type='text/csv')
        result = import_transactions(self.user, uploaded_file, source_format='generic')
        self.assertEqual(result['created_expenses'], 1)
        expense = Expense.objects.get(user=self.user)
        self.assertEqual(expense.description, 'Кава')
        self.assertEqual(expense.amount, Decimal('60'))
        self.assertEqual(expense.category, 'food')
        self.assertTrue(expense.is_emotional)
        self.assertEqual(expense.emotional_tag, 'fast_food')

    def test_tsv_import_parses_transport(self):
        content = 'date\tamount\tdescription\ttype\n2026-05-27 17:44\t-120\tтаксі\texpense\n'.encode('utf-8-sig')
        uploaded_file = SimpleUploadedFile('transactions.tsv', content, content_type='text/tab-separated-values')
        result = import_transactions(self.user, uploaded_file, source_format='generic')
        self.assertEqual(result['created_expenses'], 1)
        expense = Expense.objects.get(user=self.user)
        self.assertEqual(expense.category, 'transport')

    def test_parse_csv_file(self):
        csv_content = 'date;amount;description;type\n2026-05-27 17:44;-120;таксі;expense\n'.encode('utf-8-sig')
        uploaded_file = SimpleUploadedFile('transactions.csv', csv_content, content_type='text/csv')
        transactions = parse_bank_file(uploaded_file, source_format='generic')
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].description, 'таксі')
        self.assertEqual(transactions[0].direction, 'expense')
        self.assertEqual(transactions[0].amount, Decimal('120'))

    def test_xlsx_import_if_dependencies_available(self):
        try:
            import pandas as pd
        except Exception as exc:
            self.skipTest(f'pandas/openpyxl are not available in this environment: {exc}')

        buffer = BytesIO()
        df = pd.DataFrame([{
            'date': '2026-05-27 17:44',
            'amount': '-80',
            'description': 'торт',
            'type': 'expense',
        }])
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        uploaded_file = SimpleUploadedFile(
            'transactions.xlsx',
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        result = import_transactions(self.user, uploaded_file, source_format='generic')
        self.assertEqual(result['created_expenses'], 1)
        expense = Expense.objects.get(user=self.user)
        self.assertEqual(expense.description, 'торт')
        self.assertEqual(expense.category, 'food')
        self.assertTrue(expense.is_emotional)


class ExpenseViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('webuser', 'web@example.com', 'password123')
        self.client = Client()
        self.client.login(username='webuser', password='password123')

    def test_manual_expense_with_auto_category_sets_food(self):
        response = self.client.post(reverse('expense_create'), {
            'amount': '60',
            'description': 'Кава',
            'category': 'auto',
            'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(user=self.user)
        self.assertEqual(expense.category, 'food')
        self.assertTrue(expense.is_emotional)
        self.assertGreater(expense.ml_confidence, 0)

    def test_manual_override_category_is_respected(self):
        response = self.client.post(reverse('expense_create'), {
            'amount': '60',
            'description': 'Кава',
            'category': 'other',
            'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        expense = Expense.objects.get(user=self.user)
        self.assertEqual(expense.category, 'other')
