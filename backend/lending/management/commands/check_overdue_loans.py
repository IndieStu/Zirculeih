from django.core.management.base import BaseCommand

from lending.services import mark_overdue


class Command(BaseCommand):
    help = "Markiert durch offenen überfälligen Gewahrsam gefährdete Folgereservierungen."

    def handle(self, *args, **options):
        self.stdout.write(str(mark_overdue()))
