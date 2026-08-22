from django.urls import path
from . import views

app_name = "invest_calculator"

urlpatterns = [
    path("compound/", views.compound_calculator, name="compound_calculator"),
    path('angel/', views.angel_investor_calculator, name='angel_investor_calculator'),

]