from django.db import models
from accounts.models import Role, User

# Create your models here.
class WorkflowMaster(models.Model):
    name = models.CharField(max_length=100)
    module = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class WorkflowStep(models.Model):
    workflow = models.ForeignKey(WorkflowMaster, on_delete=models.CASCADE)

    step_order = models.IntegerField()
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    action_name = models.CharField(max_length=50)
    is_final = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.workflow.name} - Step {self.step_order}"


class WorkflowInstance(models.Model):
    workflow = models.ForeignKey(WorkflowMaster, on_delete=models.CASCADE)

    object_id = models.CharField(max_length=100)
    module = models.CharField(max_length=50)

    current_step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True
    )

    status = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)


class WorkflowHistory(models.Model):
    instance = models.ForeignKey(WorkflowInstance, on_delete=models.CASCADE)

    step = models.ForeignKey(WorkflowStep, on_delete=models.CASCADE)

    action = models.CharField(max_length=50)
    remarks = models.TextField(null=True, blank=True)

    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    performed_at = models.DateTimeField(auto_now_add=True)

    from_step = models.IntegerField(null=True)
    to_step = models.IntegerField(null=True)
