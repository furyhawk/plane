# Python imports
from urllib.parse import urlencode, urljoin

# Django imports
from django.core.validators import validate_email
from django.http import HttpResponseRedirect
from django.views import View

# Third party imports
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

# Module imports
from plane.authentication.provider.credentials.magic_code import (
    MagicCodeProvider,
)
from plane.authentication.utils.login import user_login
from plane.bgtasks.magic_link_code_task import magic_link
from plane.license.models import Instance
from plane.authentication.utils.host import base_host
from plane.db.models import User, Profile
from plane.authentication.adapter.error import (
    AuthenticationException,
    AUTHENTICATION_ERROR_CODES,
)


class MagicGenerateSpaceEndpoint(APIView):

    permission_classes = [
        AllowAny,
    ]

    def post(self, request):
        # Check if instance is configured
        instance = Instance.objects.first()
        if instance is None or not instance.is_setup_done:
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES[
                    "INSTANCE_NOT_CONFIGURED"
                ],
                error_message="INSTANCE_NOT_CONFIGURED",
            )
            return Response(
                exc.get_error_dict(), status=status.HTTP_400_BAD_REQUEST
            )

        origin = base_host(request=request)
        email = request.data.get("email", False)
        try:
            # Clean up the email
            email = email.strip().lower()
            validate_email(email)
            adapter = MagicCodeProvider(request=request, key=email)
            key, token = adapter.initiate()
            # If the smtp is configured send through here
            magic_link.delay(email, key, token, origin)
            return Response({"key": str(key)}, status=status.HTTP_200_OK)
        except AuthenticationException as e:
            return Response(
                e.get_error_dict(),
                status=status.HTTP_400_BAD_REQUEST,
            )


class MagicSignInSpaceEndpoint(View):

    def post(self, request):

        # set the referer as session to redirect after login
        code = request.POST.get("code", "").strip()
        email = request.POST.get("email", "").strip().lower()
        next_path = request.POST.get("next_path")

        if code == "" or email == "":
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES[
                    "MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED"
                ],
                error_message="MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED",
            )
            params = exc.get_error_dict()
            if next_path:
                params["next_path"] = str(next_path)
            url = urljoin(
                base_host(request=request),
                "spaces/accounts/sign-in?" + urlencode(params),
            )
            return HttpResponseRedirect(url)

        if not User.objects.filter(email=email).exists():
            params = {
                "error_code": "USER_DOES_NOT_EXIST",
                "error_message": "User could not be found with the given email.",
            }
            if next_path:
                params["next_path"] = str(next_path)
            url = urljoin(
                base_host(request=request),
                "accounts/sign-in?" + urlencode(params),
            )
            return HttpResponseRedirect(url)

        try:
            provider = MagicCodeProvider(
                request=request, key=f"magic_{email}", code=code
            )
            user = provider.authenticate()
            # Login the user and record his device info
            user_login(request=request, user=user)
            # redirect to referer path
            profile = Profile.objects.get(user=user)
            if user.is_password_autoset and profile.is_onboarded:
                path = "spaces/accounts/set-password"
            else:
                # Get the redirection path
                path = str(next_path) if next_path else "spaces"
            url = urljoin(base_host(request=request), path)
            return HttpResponseRedirect(url)

        except AuthenticationException as e:
            params = e.get_error_dict()
            if next_path:
                params["next_path"] = str(next_path)
            url = urljoin(
                base_host(request=request),
                "spaces/accounts/sign-in?" + urlencode(params),
            )
            return HttpResponseRedirect(url)


class MagicSignUpSpaceEndpoint(View):

    def post(self, request):

        # set the referer as session to redirect after login
        code = request.POST.get("code", "").strip()
        email = request.POST.get("email", "").strip().lower()
        next_path = request.POST.get("next_path")

        if code == "" or email == "":
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES[
                    "MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED"
                ],
                error_message="MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED",
            )
            params = exc.get_error_dict()
            if next_path:
                params["next_path"] = str(next_path)
            url = urljoin(
                base_host(request=request),
                "spaces/accounts/sign-in?" + urlencode(params),
            )
            return HttpResponseRedirect(url)

        if User.objects.filter(email=email).exists():
            exc = AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["USER_ALREADY_EXIST"],
                error_message="USER_ALREADY_EXIST",
            )
            params = exc.get_error_dict()
            if next_path:
                params["next_path"] = str(next_path)
            url = urljoin(
                base_host(request=request),
                "?" + urlencode(params),
            )
            return HttpResponseRedirect(url)

        try:
            provider = MagicCodeProvider(
                request=request, key=f"magic_{email}", code=code
            )
            user = provider.authenticate()
            # Login the user and record his device info
            user_login(request=request, user=user)
            # redirect to referer path
            url = urljoin(
                base_host(request=request),
                str(next_path) if next_path else "spaces",
            )
            return HttpResponseRedirect(url)

        except AuthenticationException as e:
            params = e.get_error_dict()
            if next_path:
                params["next_path"] = str(next_path)
            url = urljoin(
                base_host(request=request),
                "spaces/accounts/sign-in?" + urlencode(params),
            )
            return HttpResponseRedirect(url)