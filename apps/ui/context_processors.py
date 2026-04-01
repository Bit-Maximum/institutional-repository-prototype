from __future__ import annotations

from .services import get_registered_style_payload, get_theme_mode_choices, resolve_interface_state


def ui_context(request):
    state = getattr(request, "interface_state", None) or resolve_interface_state(request)
    return {
        "ui_state": state,
        "ui_style": state.style,
        "ui_theme_mode_choices": get_theme_mode_choices(),
        "ui_language_choices": state.available_languages,
        "ui_registered_styles": get_registered_style_payload(),
    }
