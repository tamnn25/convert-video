# payment/views.py

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from mainapps.accounts.models import User
from converterapp import settings
from mainapps.payment.models import UserSubscription
from datetime import datetime
import json
import logging
from mainapps.accounts.emails import send_html_email
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import UserSubscription
from .serializers import UserSubscriptionSerializer

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
                notify_user_account_created(user_name, user_email)

            save_user_subscription(user, payload)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "success"})


def save_user_subscription(user, payment_info):
    expiration_date = datetime.fromtimestamp(
        payment_info["data"]["object"]["expires_at"]
    )
    subscription_id = payment_info["data"]["object"]["subscription"]
    amount_allowed_usage = payment_info["data"]["object"]["amount_total"]

    try:
        subscription = UserSubscription.objects.create(
            user=user,
            status="COMPLETED",
            expiration_at=expiration_date,
            subscription_id=subscription_id,
            subscription_type="MONTH",
            payment_info=json.dumps(payment_info),
            amount_allowed_usage=amount_allowed_usage,
            amount_used_usage=0,
        )
        return subscription

    except Exception as e:
        logging.error(f"Failed to create UserSubscription: {str(e)}")
        raise Exception(str(e))


def notify_user_account_created(user_name, user_email):
    subject = "Your account has been successfully created"
    from_email = settings.DEFAULT_FROM_EMAIL
    html_file = "accounts/account_created.html"
    context = {
        "user_name": user_name,
        "user_email": user_email,
        "password_reset_link": settings.SET_PASSWORD_URL,
    }
    send_html_email(
        subject,
        "Account Creation Notification",
        from_email,
        user_email,
        html_file,
        context,
    )

class LastUserSubscriptionView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Get the latest subscription for the user
        last_subscription = UserSubscription.objects.filter(user=user).order_by('-created_at').first()

        if last_subscription:
            total = last_subscription.amount_allowed_usage - last_subscription.amount_used_usage
            # If total is 0, get the next latest subscription
            if total == 0:
                nearly_last_subscription = UserSubscription.objects.filter(user=user).exclude(id=last_subscription.id).order_by('-created_at').first()
                last_subscription = nearly_last_subscription if nearly_last_subscription else last_subscription

            serializer = UserSubscriptionSerializer(last_subscription)
            return Response(serializer.data)
        else:
            return Response({"error": "No subscriptions found"}, status=404)