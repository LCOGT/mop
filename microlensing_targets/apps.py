from django.apps import AppConfig


class CustomCodeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "microlensing_targets"
