from django.contrib import admin
from django.urls import path, include
from expenses.views import CustomLoginView, CustomLogoutView, signup_view

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', CustomLogoutView.as_view(), name='logout'),
    path('accounts/signup/', signup_view, name='signup'),

    path('', include('expenses.urls')),
]
