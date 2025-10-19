from django.db import models
from user.models import User
from workspace.models import Workspace  
from group.models import Group
import uuid

# Create your models here.
class TaskBoard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="task_boards", null=True, blank=True
    )
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="task_boards", null=True, blank=True
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name="created_task_boards"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} in {self.workspace or self.group}"
     

class TaskCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=models.UUIDField, editable=False)
    task_board = models.ForeignKey(
        TaskBoard, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} in {self.task_board}"
    
class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=models.UUIDField, editable=False)
    category = models.ForeignKey(
        TaskCategory, on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="tasks", null=True, blank=True
    )
    due_date = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} in {self.category}"