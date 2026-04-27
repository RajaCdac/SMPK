from django.db import models
from accounts.models import User


# Create your models here.
class Department(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    employee_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)

    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)

    designation = models.CharField(max_length=100)

    is_pension_user = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.employee_code}"