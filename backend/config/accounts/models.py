from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Role(models.Model):
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    def delete(self, *args, **kwargs):
        raise Exception("Roles cannot be deleted. Deactivate instead.")


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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