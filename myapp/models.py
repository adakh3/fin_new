from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import User

# Create your models here.

# If you need to add QuickBooks fields to the User model, you can create a profile model:
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    quickbooks_access_token = models.CharField(max_length=255, null=True, blank=True)
    quickbooks_refresh_token = models.CharField(max_length=255, null=True, blank=True)
    quickbooks_realm_id = models.CharField(max_length=50, null=True, blank=True)

# You can add any other models here