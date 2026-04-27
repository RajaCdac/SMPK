from django.db import models
from accounts.models import User

# Create your models here.
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]

    table_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=100)

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)

    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    changed_at = models.DateTimeField(auto_now_add=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    module = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.table_name} - {self.action}"