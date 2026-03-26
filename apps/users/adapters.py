from __future__ import annotations

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


def _derive_full_name(data: dict, fallback_email: str = "") -> str:
    name = (data.get("name") or "").strip()
    if name:
        return name
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    combined = " ".join(part for part in [first_name, last_name] if part).strip()
    if combined:
        return combined
    email_local = (fallback_email.split("@", 1)[0] if fallback_email else "").replace(".", " ").replace("_", " ").strip()
    return email_local.title() if email_local else "Пользователь Google"


class RepositorySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        email = (data.get("email") or getattr(user, "email", "") or "").strip().lower()
        if email:
            user.email = email
        user.full_name = _derive_full_name(data, fallback_email=email)
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        if not user.full_name:
            data = sociallogin.account.extra_data or {}
            user.full_name = _derive_full_name(data, fallback_email=user.email)
            user.save(update_fields=["full_name"])
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        return "/accounts/oauth/"
