from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin_mixins import LocalizedModelAdminMixin

from .models import User


class AdminRoleFilter(admin.SimpleListFilter):
    title = _("Роль администратора")
    parameter_name = "is_admin"

    def lookups(self, request, model_admin):
        return (("1", _("Администраторы")), ("0", _("Обычные пользователи")))

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(is_admin=True)
        if self.value() == "0":
            return queryset.filter(is_admin=False)
        return queryset


class StaffStatusFilter(admin.SimpleListFilter):
    title = _("Доступ в админку")
    parameter_name = "is_staff"

    def lookups(self, request, model_admin):
        return (("1", _("Есть доступ")), ("0", _("Нет доступа")))

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(is_staff=True)
        if self.value() == "0":
            return queryset.filter(is_staff=False)
        return queryset


class ActiveStatusFilter(admin.SimpleListFilter):
    title = _("Активность учётной записи")
    parameter_name = "is_active"

    def lookups(self, request, model_admin):
        return (("1", _("Активные")), ("0", _("Неактивные")))

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(is_active=True)
        if self.value() == "0":
            return queryset.filter(is_active=False)
        return queryset


@admin.register(User)
class UserAdmin(LocalizedModelAdminMixin, ModelAdmin):
    list_display = ("email_display", "full_name_display", "admin_role_display", "staff_display", "active_display")
    search_fields = ("email", "full_name")
    list_filter = (AdminRoleFilter, StaffStatusFilter, ActiveStatusFilter)
    ordering = ("email",)
    field_labels = {
        "email": _("Электронная почта"),
        "password": _("Хеш пароля"),
        "full_name": _("ФИО"),
        "is_admin": _("Администратор"),
        "is_staff": _("Есть доступ в админку"),
        "is_active": _("Учётная запись активна"),
        "groups": _("Группы"),
        "user_permissions": _("Индивидуальные права доступа"),
    }

    @display(description=_("Электронная почта"), ordering="email")
    def email_display(self, obj):
        return obj.email

    @display(description=_("ФИО"), ordering="full_name")
    def full_name_display(self, obj):
        return obj.full_name

    @display(description=_("Роль"), label={"Администратор": "success", "Пользователь": "info"})
    def admin_role_display(self, obj):
        return _("Администратор") if obj.is_admin else _("Пользователь")

    @display(description=_("Доступ в админку"), label={"Да": "success", "Нет": "warning"})
    def staff_display(self, obj):
        return _("Да") if obj.is_staff else _("Нет")

    @display(description=_("Активность"), label={"Активен": "success", "Неактивен": "danger"})
    def active_display(self, obj):
        return _("Активен") if obj.is_active else _("Неактивен")


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
