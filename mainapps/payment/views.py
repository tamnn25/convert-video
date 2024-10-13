# payment/views.py

from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from mainapps.accounts.models import User
from converterapp import settings
from mainapps.payment.models import UserSubscription

import json
import requests
import logging

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)


@csrf_exempt
@require_POST
def checkout_session_stripe(request):
    payload = json.loads(request.body.decode("utf-8"))
    logging.debug(f"[COMMAND LOGGING DATA]: {payload}")

    default_password = settings.USER_DEFAULT_PASSWORD

    if (
        payload.get("type") == "checkout.session.completed"
        and payload["data"]["object"].get("status") == "complete"
    ):
        user_email = payload["data"]["object"]["customer_details"]["email"]
        user_name = payload["data"]["object"]["customer_details"]["name"]

        try:
            hashed_password = make_password(default_password)

            user, created = User.objects.get_or_create(
                email=user_email,
                defaults={
                    "username": user_email,
                    "first_name": user_name,
                    "email": user_email,
                    "password": hashed_password,
                    "is_superuser": 0,
                },
            )
            if created:
                user.password = hashed_password
                user.save()

            save_user_subscription(user, json.dumps(payload))
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "success"})


def save_user_subscription(user, payment_info):
    try:
        expiration_date = payment_info["data"]["object"]["expires_at"]
        subscription_id = payment_info["data"]["object"]["subscription"]
        amount_allowed_usage = payment_info["data"]["object"]["amount_total"]

        # Kiểm tra kiểu dữ liệu trước khi ép kiểu
        if not isinstance(amount_allowed_usage, (int, str)):
            logging.error(f"Invalid type for amount_allowed_usage: {type(amount_allowed_usage)}")
            raise ValueError("amount_allowed_usage must be an integer or string that can be converted to an integer")

        try:
            amount_allowed_usage = int(amount_allowed_usage)
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid amount_allowed_usage value: {amount_allowed_usage}, error: {str(e)}")
            raise ValueError("amount_allowed_usage must be a valid integer")

        # Tạo đối tượng UserSubscription
        subscription = UserSubscription.objects.create(
            # user=user,
            status="COMPLETED",
            # expiration_at=expiration_date,
            # subscription_id=subscription_id,
            subscription_type="MONTH",
            # payment_info=payment_info,
            # amount_allowed_usage=amount_allowed_usage,
            # amount_used_usage=0,
        )
        return subscription

    except Exception as e:
        logging.error(f"Failed to create UserSubscription: {str(e)}")
        raise Exception(str(e))

