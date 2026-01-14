from django.db import models

# Create your models here.
class Badge(models.Model):
    key = models.CharField(max_length=50, unique=True) # Unique stable identifier for the badge
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.ImageField(null=True, blank=True)  # or ImageField
    category = models.CharField(max_length=50)  # contribution, streak, quality
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

