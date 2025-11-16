from django.db import models
from user.models import User
from workspace.models import Workspace
from group.models import Group
import uuid


class TaskBoard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="task_boards",
        null=True,
        blank=True,
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="task_boards",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255, default="Main Board")
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User, on_delete=models.DO_NOTHING, related_name="created_task_boards"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} in {self.workspace or self.group}"


class TaskList(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_board = models.ForeignKey(
        TaskBoard, on_delete=models.CASCADE, related_name="task_lists"
    )
    name = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

#TODO: optimize position assignment
    def save(self, *args, **kwargs):
        if not self.position and self.task_board:
            last_position = TaskList.objects.filter(
                task_board=self.task_board
            ).aggregate(models.Max("position"))["position__max"]
            self.position = (last_position + 1) if last_position is not None else 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} in {self.task_board}"


class TaskAssignment(models.Model):
    """Through model for better task assignment tracking"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        "Task", on_delete=models.CASCADE, related_name="assignments"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tasks_assigned_to_me",
        null=True,
        blank=True,
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_assigned_by_me",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("completed", "Completed"),
        ],
        default="pending",
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ["task", "assigned_to"]

    def __str__(self):
        return f"{self.assigned_to} assigned to {self.task.title}"


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_list = models.ForeignKey(
        TaskList, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ManyToManyField(
        User,
        through=TaskAssignment,
        through_fields=("task", "assigned_to"),
        related_name="tasks_assigned",
        blank=True,
    )
    position = models.PositiveIntegerField(default=0)
    due_date = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.position:
            last_position = Task.objects.filter(task_list=self.task_list).aggregate(
                models.Max("position")
            )["position__max"]
            self.position = (last_position + 1) if last_position is not None else 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} in {self.task_list}"
