from django.contrib.auth.models import AbstractUser
from django.db import models

from .role_codes import role_name_to_code


class User(AbstractUser):
    pass


class Role(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=30, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = role_name_to_code(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        raise Exception("Roles cannot be deleted. Deactivate instead.")


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    emp_code = models.CharField(max_length=50, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    mobile_no = models.CharField(max_length=20, blank=True)

    def __str__(self):
        name = self.user.get_full_name().strip()
        return name or self.user.username


class UserRole(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="userrole_set",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user} - {self.role}"


class DiesNon(models.Model):
    start_dt = models.DateField()
    end_date = models.DateField(default=None, null=True, blank=True)
    description = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.description
