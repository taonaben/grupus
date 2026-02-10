from django.core.management.base import BaseCommand
from apps.authentication.models import OTP


class Command(BaseCommand):
    help = "Delete all OTP tokens from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirm deletion without prompting",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            confirm = input(
                "Are you sure you want to delete ALL OTP records? (yes/no): "
            )
            if confirm.lower() != "yes":
                self.stdout.write(self.style.WARNING("Cancelled."))
                return

        deleted_count, _ = OTP.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {deleted_count} OTP records")
        )
