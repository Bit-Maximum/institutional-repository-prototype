from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True, slots=True)
class UiStyleDefinition:
    identifier: str
    label: str
    description: str
    stylesheet_path: str
    preview_hint: str = ""


_STYLE_REGISTRY: dict[str, UiStyleDefinition] = {}


def register_style(style: UiStyleDefinition) -> None:
    _STYLE_REGISTRY[style.identifier] = style


def get_registered_styles() -> list[UiStyleDefinition]:
    return list(_STYLE_REGISTRY.values())


def iter_registered_styles() -> Iterable[UiStyleDefinition]:
    return _STYLE_REGISTRY.values()


def get_style(identifier: str | None) -> UiStyleDefinition | None:
    if not identifier:
        return None
    return _STYLE_REGISTRY.get(identifier)


def get_default_style() -> UiStyleDefinition:
    default_style = get_style("academic")
    if default_style is None:
        raise RuntimeError("Default UI style 'academic' is not registered.")
    return default_style


def is_valid_style(identifier: str | None) -> bool:
    return bool(identifier and identifier in _STYLE_REGISTRY)


def style_choices_for_admin() -> list[tuple[str, str]]:
    return [(style.identifier, style.label) for style in get_registered_styles()]


register_style(
    UiStyleDefinition(
        identifier="academic",
        label=_("Академический"),
        description=_(
            "Сдержанный интерфейс с выраженной типографикой, чёткой иерархией блоков и спокойными акцентами."
        ),
        stylesheet_path="css/ui/styles/academic.css",
        preview_hint=_("Подходит для классических университетских и библиотечных репозиториев."),
    )
)

register_style(
    UiStyleDefinition(
        identifier="liquid_glass",
        label=_("Liquid Glass"),
        description=_(
            "Более современный стиль с полупрозрачными поверхностями, мягким свечением и визуальной глубиной."
        ),
        stylesheet_path="css/ui/styles/liquid-glass.css",
        preview_hint=_("Подходит для демонстрации гибкости UI и современного визуального языка."),
    )
)
