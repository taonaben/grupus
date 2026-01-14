from django.contrib import admin
from .models import Task, TaskBoard, TaskList

# Register your models here.
admin.site.register(Task)
admin.site.register(TaskBoard)
admin.site.register(TaskList)
