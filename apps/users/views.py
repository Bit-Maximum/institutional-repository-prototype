from __future__ import annotations

from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView

from apps.collections_app.models import Collection
from apps.publications.models import Publication
from apps.search.models import SearchQuery

from .forms import RegisterForm, UserProfileForm

User = get_user_model()


class OAuthContextMixin:
    def get_google_oauth_enabled(self) -> bool:
        return bool(getattr(settings, "GOOGLE_OAUTH_ENABLED", False))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_oauth_enabled"] = self.get_google_oauth_enabled()
        return context


class UserRegisterView(OAuthContextMixin, CreateView):
    form_class = RegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("login")


class UserLoginView(OAuthContextMixin, LoginView):
    template_name = "users/login.html"


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("home")


class UserProfileView(LoginRequiredMixin, OAuthContextMixin, TemplateView):
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        accounts = SocialAccount.objects.filter(user=user).order_by("provider", "date_joined")
        collection_stats = Collection.objects.filter(author_user=user).aggregate(
            total=Count("id"),
            total_publications=Count("publications", distinct=True),
        )
        publication_total = Publication.objects.filter(uploaded_by=user).count()
        publication_drafts = Publication.objects.filter(uploaded_by=user, is_draft=True).count()
        publication_published = Publication.objects.filter(uploaded_by=user, is_draft=False).count()
        context.update(
            {
                "social_accounts": accounts,
                "google_accounts": [account for account in accounts if account.provider == "google"],
                "has_local_password": user.has_usable_password(),
                "collection_count": collection_stats.get("total") or 0,
                "collection_publication_count": collection_stats.get("total_publications") or 0,
                "search_query_count": SearchQuery.objects.filter(user=user).count(),
                "uploaded_publication_count": publication_total,
                "draft_publication_count": publication_drafts,
                "published_publication_count": publication_published,
            }
        )
        return context


class UserProfileEditView(LoginRequiredMixin, OAuthContextMixin, TemplateView):
    template_name = "users/profile_edit.html"

    def get_profile_form(self):
        return UserProfileForm(instance=self.request.user)

    def get_password_form(self):
        if self.request.user.has_usable_password():
            return PasswordChangeForm(user=self.request.user)
        return SetPasswordForm(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("profile_form", kwargs.get("profile_form") or self.get_profile_form())
        context.setdefault("password_form", kwargs.get("password_form") or self.get_password_form())
        context["has_local_password"] = self.request.user.has_usable_password()
        context["social_accounts"] = SocialAccount.objects.filter(user=self.request.user).order_by("provider", "date_joined")
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "profile":
            form = UserProfileForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Профиль обновлён.")
                return redirect("profile")
            return self.render_to_response(self.get_context_data(profile_form=form, password_form=self.get_password_form()))

        if action == "password":
            form_class = PasswordChangeForm if request.user.has_usable_password() else SetPasswordForm
            password_form = form_class(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Локальный пароль обновлён.")
                return redirect("profile")
            return self.render_to_response(self.get_context_data(profile_form=self.get_profile_form(), password_form=password_form))

        messages.error(request, "Не удалось определить действие формы.")
        return redirect("profile-edit")


class OAuthConnectionsView(LoginRequiredMixin, OAuthContextMixin, TemplateView):
    template_name = "users/oauth_connections.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accounts = SocialAccount.objects.filter(user=self.request.user).order_by("provider", "date_joined")
        context["social_accounts"] = accounts
        context["google_accounts"] = [account for account in accounts if account.provider == "google"]
        context["can_disconnect_any"] = self.request.user.has_usable_password() or accounts.count() > 1
        return context


class OAuthDisconnectView(LoginRequiredMixin, View):
    def post(self, request, pk: int, *args, **kwargs):
        social_account = get_object_or_404(SocialAccount, pk=pk, user=request.user)
        total_accounts = SocialAccount.objects.filter(user=request.user).count()
        if not request.user.has_usable_password() and total_accounts <= 1:
            messages.error(
                request,
                "Нельзя отвязать последнюю OAuth-учётную запись, пока у пользователя не установлен локальный пароль.",
            )
            return redirect("oauth-settings")

        SocialToken.objects.filter(account=social_account).delete()
        provider_label = social_account.get_provider().name if hasattr(social_account, "get_provider") else social_account.provider
        social_account.delete()
        messages.success(request, f"Связь с провайдером {provider_label} удалена.")
        return redirect("oauth-settings")
