from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.authentication.models import OTP


class Command(BaseCommand):
    help = "Delete expired OTP tokens from the database"

    def handle(self, *args, **options):
        deleted_count, _ = OTP.objects.filter(expires_at__lt=timezone.now()).delete()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {deleted_count} expired OTPs")
        )
