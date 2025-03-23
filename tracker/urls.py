from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, predict_savings

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('predict/', predict_savings, name='predict_savings'),
]