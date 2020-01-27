from django.urls import path, include

from . import views

urlpatterns = [
    path('count', views.ManageCount.as_view()),
    path('calc', views.Calc.as_view()),
    path('statistic', views.Statistic.as_view()),
    path('withdraw/', views.WithdrawStatisticsAPI.as_view()),
    path('recharge/', views.RechargeStatisticsAPI.as_view()),
    path('wxuser/', views.WxUserStatisticsAPI.as_view()),
    path('order/', views.OrderStatisticsAPI.as_view()),
    path('feedback/', views.FeedbackStatisticsAPI.as_view()),
    path('turnovers/', views.TurnoversStatisticsAPI.as_view()),
    path('level/', views.LevelStatisticsAPI.as_view()),
    path('qconline/', views.OnlineAPI.as_view()),
]