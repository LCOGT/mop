from django.apps import AppConfig


class CustomCodeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "microlensing_targets"

    def nav_items(self):
        """
        Integration point for adding items to the navbar.
        This method should return a list of partial templates to be included in the navbar.
        """
        return [{'partial': 'microlensing_targets/partials/navbar_items_list.html'}]