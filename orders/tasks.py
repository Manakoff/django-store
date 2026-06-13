from celery import shared_task
from django.db import transaction

from orders.models import Order


@shared_task
def complete_order_payment_task(order_id):
    try:

        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)

            if order.status == Order.PAID:
                return f"Order #{order_id} was already processed."

            order.update_after_payment()

            return f"Order #{order_id} successfully updated via Celery."

    except Order.DoesNotExist:
        return f"Order #{order_id} not found."
