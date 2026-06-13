from django.urls import path

from orders.views import (OrderCreateView, OrderDetailView, OrderListView,
                          OrderPaymentCheckView, SuccessTemplateView,
                          YookassaWebhookView)

app_name = "orders"

urlpatterns = [
    path("order-create/", OrderCreateView.as_view(), name="order_create"),
    path('', OrderListView.as_view(), name="orders_list"),
    path('order/<int:pk>/', OrderDetailView.as_view(), name="order"),
    path("order-success/", SuccessTemplateView.as_view(), name="order_success"),
    path('webhook/yookassa/', YookassaWebhookView.as_view(), name='yookassa_webhook'),
    path("order-payment-check/", OrderPaymentCheckView.as_view(), name="order_payment_check"),
]
