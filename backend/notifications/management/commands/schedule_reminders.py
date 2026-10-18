from django.core.management.base import BaseCommand

from notifications.reminders import schedule


class Command(BaseCommand):
    help = "Bereitet idempotente Abhol-/Rückgabe-/Überziehungserinnerungen vor."

    def handle(self, *args, **options):
        self.stdout.write(str(schedule()))
