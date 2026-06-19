import json
import uuid

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from yookassa import Configuration, Payment

from common.views import TitleMixin
from orders.forms import OrderForm
from orders.models import Order
from orders.tasks import complete_order_payment_task

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


class SuccessTemplateView(TitleMixin, TemplateView):
    template_name = "orders/success.html"
    title = "Store - Спасибо за заказ!"


class OrderListView(ListView):
    template_name = "orders/orders.html"
    title = "Store - Заказы"
    queryset = Order.objects.all()
    ordering = "-created"

    def get_queryset(self):
        queryset = super(OrderListView, self).get_queryset()
        return queryset.filter(initiator=self.request.user)


class OrderDetailView(DetailView):
    template_name = "orders/order.html"
    model = Order

    def get_context_data(self, **kwargs):
        context = super(OrderDetailView, self).get_context_data(**kwargs)
        context["title"] = f"Store - Заказ №{self.object.id}"
        return context


class OrderCreateView(TitleMixin, CreateView):
    template_name = "orders/order_create.html"
    form_class = OrderForm
    success_url = reverse_lazy("orders:order_create")
    title = "Store - Оформление заказа"

    def form_valid(self, form):

        form.instance.initiator = self.request.user

        baskets = self.request.user.basket_set.all()
        total_price = baskets.total_sum()

        order = form.save()

        description = (
            f"Оплата товаров в магазине Store для {self.request.user.username}"
        )
        payment = Payment.create(
            {
                "amount": {"value": str(total_price), "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": self.request.build_absolute_uri(
                        reverse("orders:order_payment_check")
                    ),
                },
                "capture": True,
                "description": description,
            },
            uuid.uuid4(),
        )

        order.payment_id = payment.id
        order.save()

        self.request.session["current_payment_id"] = payment.id

        return HttpResponseRedirect(payment.confirmation.confirmation_url)


class OrderPaymentCheckView(View):
    def get(self, request, *args, **kwargs):
        payment_id = request.session.get("current_payment_id")

        if not payment_id:
            return redirect("orders:order_create")

        try:
            payment_info = Payment.find_one(payment_id)
            order = Order.objects.get(payment_id=payment_id)

            if payment_info.status in ["succeeded", "pending"]:
                complete_order_payment_task.delay(order.id)
                return redirect("orders:order_success")

            elif payment_info.status == "canceled":
                order.status = Order.CANCELED
                order.save()

                return redirect("orders:order_create")

            elif payment_info.status == "pending":
                order.update_after_payment()
                return redirect("orders:order_success")

        except Exception:
            return redirect("orders:order_create")

        return redirect("orders:order_create")


@method_decorator(csrf_exempt, name="dispatch")
class YookassaWebhookView(View):
    def post(self, request, *args, **kwargs):
        try:

            event_data = json.loads(request.body.decode("utf-8"))

            if event_data.get("event") == "payment.succeeded":
                payment_object = event_data.get("object", {})
                payment_id = payment_object.get("id")

                order = Order.objects.get(payment_id=payment_id)

                complete_order_payment_task.delay(order.id)

            elif event_data.get("event") == "payment.canceled":
                payment_object = event_data.get("object", {})
                payment_id = payment_object.get("id")

                order = Order.objects.get(payment_id=payment_id)
                if order.status != Order.PAID:
                    order.status = Order.CANCELED
                    order.save()

        except Order.DoesNotExist:
            pass

        except Exception:
            return HttpResponse(status=400)

        return HttpResponse(status=200)
