from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('expenses/edit/<int:pk>/', views.expense_edit, name='expense_edit'),
    path('expenses/delete/<int:pk>/', views.expense_delete, name='expense_delete'),

    path('incomes/', views.income_list, name='income_list'),
    path('budgets/', views.budget_list, name='budget_list'),

    path('transactions/import/', views.transaction_import, name='transaction_import'),
    path('transactions/export/', views.transaction_export, name='transaction_export'),

    path('analytics/emotions/', views.emotional_report, name='emotional_report'),
]