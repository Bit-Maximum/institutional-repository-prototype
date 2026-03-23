from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "is_admin")
    search_fields = ("email", "full_name")
    list_filter = ("is_admin",)
    ordering = ("email",)
