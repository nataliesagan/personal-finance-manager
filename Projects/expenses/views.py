import csv
import json
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .emotion_rules import analyze_emotional_expense
from .forms import (
    ExpenseForm,
    SignUpForm,
    IncomeForm,
    CategoryBudgetForm,
    TransactionImportForm,
)
from .models import Expense, Income, CategoryBudget, CategoryFeedback
from .services.bank_io import import_transactions, safe_predict_expense_category
from .services.emotional_advice import build_emotional_advice

logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'


class CustomLogoutView(LogoutView):
    pass


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    month_start = today.replace(day=1)

    expenses_qs = Expense.objects.filter(user=user, created_at__date__gte=month_start)
    incomes_qs = Income.objects.filter(user=user, created_at__date__gte=month_start)
    today_expenses = Expense.objects.filter(user=user, created_at__date=today)

    total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or 0
    total_incomes = incomes_qs.aggregate(total=Sum('amount'))['total'] or 0
    balance = total_incomes - total_expenses

    by_category = list(expenses_qs.values('category').annotate(total=Sum('amount')).order_by('-total'))
    cat_labels = [dict(Expense.CATEGORY_CHOICES)[item['category']] for item in by_category]
    cat_values = [float(item['total']) for item in by_category]
    category_breakdown = [
        {
            'name': dict(Expense.CATEGORY_CHOICES)[item['category']],
            'total': float(item['total']),
        }
        for item in by_category
    ]

    emotional_total = expenses_qs.filter(is_emotional=True).aggregate(total=Sum('amount'))['total'] or 0
    emotional_percent = float(emotional_total) / float(total_expenses) * 100 if total_expenses else 0.0

    date_from = today - timedelta(days=30)
    expenses_30 = Expense.objects.filter(user=user, created_at__date__gte=date_from)
    by_day_exp = (
        expenses_30
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )
    day_labels = [str(item['day']) for item in by_day_exp]
    day_values = [float(item['total']) for item in by_day_exp]

    incomes_30 = Income.objects.filter(user=user, created_at__date__gte=date_from)
    by_day_inc = (
        incomes_30
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )

    exp_by_day_dict = {str(item['day']): float(item['total']) for item in by_day_exp}
    inc_by_day_dict = {str(item['day']): float(item['total']) for item in by_day_inc}

    all_days = sorted(set(exp_by_day_dict.keys()) | set(inc_by_day_dict.keys()))
    cashflow_labels = all_days
    cashflow_incomes = [inc_by_day_dict.get(d, 0.0) for d in all_days]
    cashflow_expenses = [exp_by_day_dict.get(d, 0.0) for d in all_days]

    budgets = CategoryBudget.objects.filter(user=user)
    budget_stats = []
    for budget in budgets:
        spent = expenses_qs.filter(category=budget.category).aggregate(total=Sum('amount'))['total'] or 0
        percent = float(spent) / float(budget.monthly_limit) * 100 if budget.monthly_limit > 0 else 0
        budget_stats.append({
            'category_code': budget.category,
            'category_name': dict(Expense.CATEGORY_CHOICES)[budget.category],
            'spent': float(spent),
            'limit': float(budget.monthly_limit),
            'percent': percent,
        })

    advice_list = build_emotional_advice(list(today_expenses), list(expenses_qs.filter(is_emotional=True)))

    context = {
        'total_expenses': total_expenses,
        'total_incomes': total_incomes,
        'balance': balance,
        'emotional_total': emotional_total,
        'emotional_percent': emotional_percent,
        'advice_list': advice_list,

        'cat_labels_json': json.dumps(cat_labels),
        'cat_values_json': json.dumps(cat_values),
        'day_labels_json': json.dumps(day_labels),
        'day_values_json': json.dumps(day_values),
        'cashflow_labels_json': json.dumps(cashflow_labels),
        'cashflow_incomes_json': json.dumps(cashflow_incomes),
        'cashflow_expenses_json': json.dumps(cashflow_expenses),

        'budget_stats': budget_stats,
        'category_breakdown': category_breakdown,
    }
    return render(request, 'expenses/dashboard.html', context)


@login_required
def expense_list(request):
    qs = Expense.objects.filter(user=request.user)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    context = {
        'expenses': qs,
    }

    if request.headers.get('HX-Request') == 'true':
        return render(request, 'expenses/partials/_expense_table.html', context)
    return render(request, 'expenses/expense_list.html', context)


@login_required
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user

            cat, conf = safe_predict_expense_category(expense.description)
            valid_categories = {c[0] for c in Expense.CATEGORY_CHOICES}

            logger.info(
                'ML predicted category=%s, conf=%.3f for user=%s',
                cat, conf, request.user.id
            )

            if conf < 0.5:
                manual_cat = form.cleaned_data.get('category') or 'other'
                expense.category = manual_cat if manual_cat in valid_categories else 'other'
            else:
                predicted_cat = cat if cat in valid_categories else 'other'
                manual_cat = form.cleaned_data.get('category')
                if manual_cat and manual_cat in valid_categories and manual_cat != predicted_cat:
                    expense.category = manual_cat
                else:
                    expense.category = predicted_cat

            expense.ml_confidence = conf

            now_dt = timezone.now()
            is_emotional, tag = analyze_emotional_expense(expense.description, expense.category, now_dt)
            expense.is_emotional = is_emotional
            expense.emotional_tag = tag

            expense.save()
            messages.success(request, 'Витрату успішно додано.')

            if request.headers.get('HX-Request') == 'true':
                qs = Expense.objects.filter(user=request.user)
                return render(request, 'expenses/partials/_expense_table.html', {'expenses': qs})
            return redirect('expense_list')
    else:
        form = ExpenseForm()

    if request.headers.get('HX-Request') == 'true':
        return render(request, 'expenses/partials/_expense_form.html', {'form': form})
    return render(request, 'expenses/expense_form.html', {'form': form})


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    old_category = expense.category

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            expense = form.save(commit=False)
            new_category = expense.category

            is_emotional, tag = analyze_emotional_expense(expense.description, expense.category, expense.created_at)
            expense.is_emotional = is_emotional
            expense.emotional_tag = tag
            expense.save()

            if old_category != new_category:
                CategoryFeedback.objects.update_or_create(
                    expense=expense,
                    defaults={
                        'original_category': old_category,
                        'corrected_category': new_category,
                    }
                )

            messages.success(request, 'Витрату оновлено.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'expenses/expense_edit.html', {
        'form': form,
        'expense': expense,
    })


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    expense.delete()
    messages.success(request, 'Витрату видалено.')
    if request.headers.get('HX-Request') == 'true':
        qs = Expense.objects.filter(user=request.user)
        return render(request, 'expenses/partials/_expense_table.html', {'expenses': qs})
    return redirect('expense_list')


@login_required
def income_list(request):
    incomes = Income.objects.filter(user=request.user).order_by('-created_at')

    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            messages.success(request, 'Дохід успішно додано.')
            return redirect('income_list')
    else:
        form = IncomeForm()

    return render(request, 'expenses/income_list.html', {
        'incomes': incomes,
        'form': form,
    })


@login_required
def budget_list(request):
    budgets = CategoryBudget.objects.filter(user=request.user)

    if request.method == 'POST':
        form = CategoryBudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            existing = CategoryBudget.objects.filter(
                user=request.user,
                category=budget.category
            ).first()
            if existing:
                existing.monthly_limit = budget.monthly_limit
                existing.save()
            else:
                budget.save()
            messages.success(request, 'Бюджет збережено.')
            return redirect('budget_list')
    else:
        form = CategoryBudgetForm()

    return render(request, 'expenses/budget_list.html', {
        'budgets': budgets,
        'form': form,
    })


@login_required
def transaction_import(request):
    if request.method == 'POST':
        form = TransactionImportForm(request.POST, request.FILES)
        if form.is_valid():
            stats = import_transactions(
                request.user,
                form.cleaned_data['file'],
                source_format=form.cleaned_data['source_format'],
            )
            if stats['created_expenses'] or stats['created_incomes']:
                messages.success(
                    request,
                    f"Імпорт завершено: витрат {stats['created_expenses']}, доходів {stats['created_incomes']}, пропущено дублікатів {stats['skipped_duplicates']}."
                )
            else:
                messages.warning(request, 'Імпорт не додав нових операцій. Можливо, всі записи вже існують.')
            for err in stats['errors'][:3]:
                messages.error(request, f'Помилка імпорту: {err}')
            return redirect('transaction_import')
    else:
        form = TransactionImportForm()

    return render(request, 'expenses/transaction_import.html', {'form': form})


@login_required
def transaction_export(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = timezone.localtime().strftime('finance_export_%Y%m%d_%H%M.csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'type', 'date', 'amount', 'category', 'description',
        'notes', 'is_emotional', 'emotional_tag', 'ml_confidence'
    ])

    expenses = Expense.objects.filter(user=request.user).order_by('-created_at')
    incomes = Income.objects.filter(user=request.user).order_by('-created_at')

    for expense in expenses:
        writer.writerow([
            'expense',
            timezone.localtime(expense.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            expense.amount,
            expense.category,
            expense.description,
            expense.notes,
            'yes' if expense.is_emotional else 'no',
            expense.emotional_tag,
            expense.ml_confidence,
        ])

    for income in incomes:
        writer.writerow([
            'income',
            timezone.localtime(income.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            income.amount,
            income.category,
            income.description,
            '',
            '',
            '',
            '',
        ])

    return response


@login_required
def emotional_report(request):
    user = request.user
    today = timezone.localdate()
    month_start = today.replace(day=1)

    expenses_qs = Expense.objects.filter(user=user, created_at__date__gte=month_start)
    emotional_qs = expenses_qs.filter(is_emotional=True)

    total = expenses_qs.aggregate(total=Sum('amount'))['total'] or 0
    emotional_total = emotional_qs.aggregate(total=Sum('amount'))['total'] or 0
    emotional_percent = float(emotional_total) / float(total) * 100 if total else 0.0

    by_tag = emotional_qs.values('emotional_tag').annotate(total=Sum('amount')).order_by('-total')
    tag_labels = []
    tag_values = []
    for item in by_tag:
        if item['emotional_tag'] == 'none':
            continue
        tag_labels.append(dict(Expense.EMOTIONAL_TAG_CHOICES)[item['emotional_tag']])
        tag_values.append(float(item['total']))

    exp_agg = (
        expenses_qs
        .annotate(day=TruncDate('created_at'))
        .values('day', 'is_emotional')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )
    day_map = {}
    for row in exp_agg:
        day = str(row['day'])
        if day not in day_map:
            day_map[day] = {'emotional': 0.0, 'normal': 0.0}
        if row['is_emotional']:
            day_map[day]['emotional'] += float(row['total'])
        else:
            day_map[day]['normal'] += float(row['total'])

    emo_days_labels = sorted(day_map.keys())
    emo_values = [day_map[d]['emotional'] for d in emo_days_labels]
    normal_values = [day_map[d]['normal'] for d in emo_days_labels]

    top_days = sorted(
        [{'day': d, 'amount': v['emotional']} for d, v in day_map.items()],
        key=lambda x: x['amount'],
        reverse=True
    )[:5]

    top_tag_name = tag_labels[0] if tag_labels else None
    advice_list = build_emotional_advice(
        list(Expense.objects.filter(user=user, created_at__date=today)),
        list(emotional_qs),
    )

    context = {
        'total': total,
        'emotional_total': emotional_total,
        'emotional_percent': emotional_percent,

        'tag_labels_json': json.dumps(tag_labels),
        'tag_values_json': json.dumps(tag_values),

        'emo_days_labels_json': json.dumps(emo_days_labels),
        'emo_values_json': json.dumps(emo_values),
        'normal_values_json': json.dumps(normal_values),

        'top_days': top_days,
        'top_tag_name': top_tag_name,
        'advice_list': advice_list,
    }
    return render(request, 'expenses/emotional_report.html', context)