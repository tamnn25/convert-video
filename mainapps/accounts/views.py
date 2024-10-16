from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model
from mainapps.accounts.emails import send_user_password_email
from mainapps.accounts.models import Credit, User
import stripe

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt

# Set the Stripe secret key
from django.http import HttpResponse

from django.contrib.auth import login as auth_login
from django.db import IntegrityError
import stripe
from django.contrib import messages
from django.urls import reverse
from djstripe.models import Subscription, Customer, Product, Subscription, APIKey, Plan
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from djoser.views import TokenCreateView
from django.contrib.auth import logout
from rest_framework.response import Response
from rest_framework import status
from djoser.views import UserViewSet
from .serializers import CustomUserCreateSerializer, CustomLoginSerializer

def logout_view(request):
    """
    Logs out the user and redirects to the login page or homepage.
    """
    # Log the user out
    logout(request)

    # Add a success message
    messages.success(request, "You have been Successfully Logged Out.")

    # Redirect to the login page or homepage
    return redirect(
        "/"
    )  # Replace 'login' with the name of the URL to redirect to (e.g., 'home' or 'login')


def send_registration_email(user, password, request):
    subject = "Welcome to Our Platform!"
    from_email = "no-reply@example.com"
    to = user.email

    # Prepare the context for the email template
    context = {
        "user": user,
        "password": password,
        "password_reset_link": request.build_absolute_uri(reverse("password_reset")),
    }

    # Render the HTML template
    html_content = render_to_string("partials/regiter_email.html", context)
    text_content = strip_tags(html_content)  # Fallback for plain text email

    # Create the email
    email = EmailMultiAlternatives(subject, text_content, from_email, [to])
    email.attach_alternative(html_content, "text/html")

    # Send the email
    email.send()


from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy


class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    success_url = reverse_lazy("password_reset_done")


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


# Create your views here.
def login(request):
    print(212121)
    if request.method == "POST":
        # Get username and password from the form
        username = request.POST["username"]
        password = request.POST["password"]

        # Authenticate the user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # If the user exists, log them in
            auth_login(request, user)  # Note: Using `auth_login` here to avoid conflict
            messages.success(request, "Successfully Logged In!")
            try:
                return redirect(request.session.get("next"))
            except:
                return redirect("/text")

        else:
            # If login failed, send an error message
            messages.error(request, "Invalid username or password. Please try again.")
    next = request.GET.get("next", "")
    request.session["next"] = next
    return render(
        request,
        "accounts/login.html",
    )


@require_POST
def payment_method(request):
    plan = request.POST.get("plan")
    automatic = request.POST.get("automatic")
    payment_meth = request.POST.get("payment_method")


def embedded_pricing_page(request):
    return render(
        request,
        "accounts/embed_stripe.html",
        #     {
        #     'stripe_public_key': djstripe_settings.STRIPE_PUBLIC_KEY,
        #     'stripe_pricing_table_id': settings.STRIPE_PRICING_TABLE_ID,
        # }
    )


@csrf_exempt
def stripe_webhook(request):
    # Get the Stripe API key from the dj-stripe APIKey model
    stripe_api_key = APIKey.objects.filter(livemode=True, type="secret").first()
    stripe.api_key = stripe_api_key.secret if stripe_api_key else None

    # Proceed only if the API key is found
    if not stripe.api_key:
        return HttpResponse("Stripe API key not found", status=500)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    endpoint_secret = (
        stripe_api_key.djstripe_owner_account.webhook_secret
    )  # Assuming webhook secret is stored in the account model

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session["customer_details"]["email"]
        subscription_id = session["subscription"]

        # Implement user creation and subscription processing here

    return HttpResponse(status=200)


def subscription_confirm(request):
    stripe_api_key = APIKey.objects.filter(livemode=False, type="secret").first()
    if not stripe_api_key:
        messages.error(request, "Stripe API key not found.")
        return HttpResponseRedirect(
            reverse("home:home")
        )  # Update with correct view name

    # Set the Stripe API key dynamically
    stripe.api_key = str(stripe_api_key.secret)

    # Get the session ID from the URL
    session_id = request.GET.get("session_id")
    if not session_id:
        messages.error(request, "Session ID is missing.")
        return HttpResponseRedirect(
            reverse("home:home")
        )  # Update with correct view name

    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)

        # Extract customer email and subscription ID from the session
        customer_email = session.customer_details.email
        subscription_id = session.subscription
        customer_name = session.customer_details.name  # Get the name
        # Retrieve or create the customer from Stripe data
        stripe_customer = stripe.Customer.retrieve(session.customer)

        # Check if there's an existing user or create a new one based on the customer email
        User = get_user_model()
        user, user_created = User.objects.get_or_create(
            email=customer_email,
            defaults={
                "username": customer_email,
                "password": User.objects.make_random_password(),
                "first_name": (
                    customer_name.split()[0] if customer_name else ""
                ),  # Save first name
                "last_name": (
                    " ".join(customer_name.split()[1:])
                    if customer_name and len(customer_name.split()) > 1
                    else ""
                ),  # Save last name
            },
        )

        # Link the user to the Stripe customer
        djstripe_customer, created = Customer.get_or_create(subscriber=user)
        # Sync the subscription from Stripe

        user.save()

        # Automatically log the user in
        subscription = stripe.Subscription.retrieve(subscription_id)
        stripe_product_id = subscription["items"]["data"][0]["plan"]["product"]

        # Retrieve the product from the database
        try:
            djstripe_product = Product.objects.get(id=stripe_product_id)
        except Product.DoesNotExist:
            messages.error(request, "Product not found in the database.")
            return HttpResponseRedirect(
                reverse("home:home")
            )  # Update with correct view name

        # Define credits based on the product
        product_credits = {
            "prod_QsWVUlHaCH4fqL": 25,  # Credits for a basic plan
            "prod_QsWWDNjdR6j22q": 50,  # Credits for a premium plan
            "prod_QsWWaDzX83oGhP": 100,
            "prod_QrRbiNv4BrEp4L": 25,
            "prod_QrRcSTxkwx207Z": 50,
            "prod_QrRcGMHuLrp4Lz": 100,
        }
        credits = product_credits.get(stripe_product_id, 0)

        # Create or update the user's credits based on the product
        Credit.create_or_update_credit(
            user=user, product=djstripe_product, credits=credits
        )
        # plan = Plan.objects.get(product__id=stripe_product_id)  # Replace with the actual Product ID

        # # Step 3: Create the subscription using the Plan
        # stripe_subscription = djstripe_customer.subscribe(
        #     items=[{
        #         "plan": plan.id  # The plan the user is subscribing to
        #     }]
        # )
        # Automatically l
        auth_login(request, user)
        # Success message
        if user_created:
            if not user.first_name or not user.last_name:
                user.first_name = customer_name.split()[0] if customer_name else ""
                user.last_name = (
                    " ".join(customer_name.split()[1:])
                    if customer_name and len(customer_name.split()) > 1
                    else ""
                )
                user.save()
            send_user_password_email(user)

            messages.success(
                request,
                "You've successfully signed up, and an account was created for you!",
            )
        else:

            # send_user_password_email(user)
            messages.success(request, "Your subscription was successfully updated!")

        return HttpResponseRedirect(
            reverse("video_text:add_text")
        )  # Update with correct view name

    except stripe.error.StripeError as e:
        # Handle Stripe-related errors
        messages.error(request, f"Stripe error: {e}")
        return HttpResponseRedirect(
            reverse("home:home")
        )  # Update with correct view name

    except IntegrityError:
        # Handle database errors
        messages.error(request, "Error creating your account. Please contact support.")
        return HttpResponseRedirect(
            reverse("home:home")
        )  # Update with correct view name

    except Exception as e:
        # Catch any other unforeseen errors
        messages.error(request, f"An unexpected error occurred.{e}")
        return HttpResponseRedirect(
            reverse("home:home")
        )  # Update with correct view name


# class CustomPasswordResetView(auth_views.PasswordResetView):
#     template_name = 'registration/password_reset_form.html'
#     email_template_name = 'registration/password_reset_email.html'
#     success_url = reverse_lazy('password_reset_done')

# class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
#     template_name = 'registration/password_reset_confirm.html'
#     success_url = reverse_lazy('password_reset_complete')


# views.py


class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"


class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = "/accounts/login"


class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


def subscription_details(request):
    user = request.user
    customer = Customer.objects.filter(subscriber=user).first()

    if customer:
        # Get the active subscription for the customer
        subscription = Subscription.objects.filter(
            customer=customer, status="active"
        ).first()

        if subscription:
            current_plan = subscription.plan
            all_plans = Plan.objects.filter(active=True).exclude(
                id=current_plan.id
            )  # Get all other active plans

            context = {
                "subscription": subscription,
                "current_plan": current_plan,
                "all_plans": all_plans,
            }
            return render(request, "subscription/details.html", context)

    return render(
        request, "accounts/details.html"
    )  # In case the user has no subscription

class CustomUserViewSet(UserViewSet):
    serializer_class = CustomUserCreateSerializer

    def perform_create(self, serializer):
        # Add custom behavior before saving
        super().perform_create(serializer)
        # Add any additional actions you want to take upon registration


from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
import json
import re


@csrf_exempt
@require_POST
def change_password(request):

    try:
        payload = json.loads(request.body)
        email = payload.get("email")
        new_password = payload.get("new_password")
        confirm_password = payload.get("confirm_password")
        user = User.objects.filter(email=email).first()

        if not user:
            return JsonResponse({"error": "Please Provide Both Email And Password."}, status=404)
        elif user.is_first_password_set:
            return JsonResponse({"error": "No Account Found With This Email. Please Check And Try Again."}, status=400)

        validation_error = validate_password_data(email, new_password, confirm_password)
        
        if validation_error:
            return validation_error

        user.password = make_password(new_password)
        user.is_first_password_set = True
        user.save()

        return JsonResponse(
            {"status": "success", "message": "Password Has Been Updated Successfully"},
            status=200,
        )

    except ObjectDoesNotExist:
        return JsonResponse(
            {
                "error": "User Does Not Exist Or Has Already Been Created In The System. Please Contact Admin For Assistance."
            },
            status=404,
        )

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def validate_password_data(email, new_password, confirm_password):
    errors = {}

    if not email:
        errors["email"] = "Email is required"
    else:
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, email):
            errors["email"] = "Invalid email format"

    if not new_password:
        errors["new_password"] = "New password is required"
    elif len(new_password) < 4:
        errors["new_password"] = "The new password must be at least 4 characters long"

    if not confirm_password:
        errors["confirm_password"] = "Confirm password is required"
    elif len(confirm_password) < 4:
        errors["confirm_password"] = (
            "The confirm password must be at least 4 characters long"
        )

    if new_password and confirm_password and new_password != confirm_password:
        errors["password_mismatch"] = "New password and confirm password do not match"

    if errors:
        return JsonResponse({"errors": errors}, status=400)

    return None

from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
class CustomLoginView(TokenCreateView):
    serializer_class = CustomLoginSerializer

    def _action(self, serializer):
        # The user is set in the validated data by the serializer
        user = serializer.validated_data.get('user')

        if user is None:
            raise AuthenticationFailed('User Authentication Failed')

        # Manually retrieve or create the auth token for the user
        token, created = Token.objects.get_or_create(user=user)

        # Return the token in the desired JSON format
        return Response({
            'auth_token': token.key
        }, status=status.HTTP_200_OK)