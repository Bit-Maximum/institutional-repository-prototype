from __future__ import annotations

from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.dispatch import receiver


def _best_name(extra_data: dict, email: str) -> str:
    name = (extra_data.get("name") or "").strip()
    if name:
        return name
    given = (extra_data.get("given_name") or extra_data.get("first_name") or "").strip()
    family = (extra_data.get("family_name") or extra_data.get("last_name") or "").strip()
    combo = " ".join(part for part in [given, family] if part).strip()
    if combo:
        return combo
    local = (email.split("@", 1)[0] if email else "").replace(".", " ").replace("_", " ").strip()
    return local.title() if local else ""


def _sync_user_profile(sociallogin) -> None:
    user = sociallogin.user
    extra = sociallogin.account.extra_data or {}
    changed_fields: list[str] = []

    email = (extra.get("email") or user.email or "").strip().lower()
    if email and email != user.email:
        user.email = email
        changed_fields.append("email")

    best_name = _best_name(extra, email or user.email)
    if best_name and (not user.full_name or user.full_name == user.email):
        user.full_name = best_name
        changed_fields.append("full_name")

    if changed_fields:
        user.save(update_fields=changed_fields)


@receiver(social_account_added)
def social_account_added_handler(request, sociallogin, **kwargs):
    _sync_user_profile(sociallogin)


@receiver(social_account_updated)
def social_account_updated_handler(request, sociallogin, **kwargs):
    _sync_user_profile(sociallogin)
