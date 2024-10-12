# payment/urls.py

from django.urls import path

from .views import checkout_session_stripe
app_name = 'payment'
urlpatterns = [
    path("stripes/webhook-checkout-sessions", checkout_session_stripe, name="stripes-webhook-checkout-session"),
]
