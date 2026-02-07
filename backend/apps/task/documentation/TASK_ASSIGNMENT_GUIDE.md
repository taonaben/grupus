# Task Assignment with GenericForeignKey - Implementation Guide

## Overview
Tasks can now be assigned to either **Users** or **Groups** using Django's GenericForeignKey.

## Model Structure

### TaskAssignment (models.py)
```python
class TaskAssignment(models.Model):
    task = models.ForeignKey("Task", on_delete=models.CASCADE, related_name="assignments")
    
    # GenericForeignKey fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    assigned_to = GenericForeignKey("content_type", "object_id")
    
    assigned_by = models.ForeignKey(User, ...)
    assigned_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(...)
    
    class Meta:
        unique_together = ["task", "content_type", "object_id"]  # Prevents duplicate assignments
```

**Key Points:**
- `content_type` stores whether it's a User or Group
- `object_id` stores the UUID of the User or Group
- `assigned_to` is the GenericForeignKey that gives you the actual object
- No `assigned_to` ManyToManyField on Task model (it's handled through `task.assignments.all()`)

## API Usage

### Creating a Task with Assignments

**Request Format:**
```json
POST /api/tasks/
{
  "task_list": "uuid-of-task-list",
  "title": "Complete the project",
  "description": "Description here",
  "assigned_to": [
    {
      "type": "user",
      "id": "user-uuid-here"
    },
    {
      "type": "group",
      "id": "group-uuid-here"
    }
  ],
  "due_date": "2026-02-10T12:00:00Z"
}
```

**Response:**
```json
{
  "id": "task-uuid",
  "task_list": "task-list-uuid",
  "title": "Complete the project",
  "description": "Description here",
  "assignments": [
    {
      "id": "assignment-uuid-1",
      "assigned_to_detail": {
        "type": "user",
        "id": "user-uuid",
        "username": "john_doe",
        "email": "john@example.com"
      },
      "assigned_by": "creator-user-uuid",
      "assigned_at": "2026-02-04T10:00:00Z",
      "status": "pending"
    },
    {
      "id": "assignment-uuid-2",
      "assigned_to_detail": {
        "type": "group",
        "id": "group-uuid",
        "name": "Development Team",
        "member_count": 5
      },
      "assigned_by": "creator-user-uuid",
      "assigned_at": "2026-02-04T10:00:00Z",
      "status": "pending"
    }
  ],
  "position": 1,
  "due_date": "2026-02-10T12:00:00Z",
  "is_completed": false,
  "created_at": "2026-02-04T10:00:00Z",
  "updated_at": "2026-02-04T10:00:00Z"
}
```

## Serializer Structure

### TaskSerializer
- **Write:** Accepts `assigned_to` as a list of `{"type": "user/group", "id": "uuid"}`
- **Read:** Returns `assignments` with full details via `TaskAssignmentSerializer`

### TaskAssignmentSerializer
- **Write:** Uses `assigned_to_type` and `assigned_to_id`
- **Read:** Returns `assigned_to_detail` with full User or Group information

## View Logic (task_card_views.py)

```python
# In CreateTaskView.create()
assigned_to_data = request.data.get("assigned_to", [])

for assignment in assigned_to_data:
    if assignment["type"] == "user":
        user = User.objects.get(id=assignment["id"])
        content_type = ContentType.objects.get_for_model(User)
        TaskAssignment.objects.create(
            task=task,
            content_type=content_type,
            object_id=user.id,
            assigned_by=request.user,
        )
    elif assignment["type"] == "group":
        group = Group.objects.get(id=assignment["id"])
        content_type = ContentType.objects.get_for_model(Group)
        TaskAssignment.objects.create(
            task=task,
            content_type=content_type,
            object_id=group.id,
            assigned_by=request.user,
        )
```

## Validation

The serializer validates that:
1. Users are members of the workspace/group
2. Groups belong to the workspace or are the task board's group
3. Assignment types are either "user" or "group"
4. No duplicate assignments (enforced by `unique_together`)

## Querying Assignments

```python
# Get all assignments for a task
task.assignments.all()

# Get the assigned entity (User or Group)
for assignment in task.assignments.all():
    print(assignment.assigned_to)  # Returns User or Group instance
    
# Filter by type
from django.contrib.contenttypes.models import ContentType

user_ct = ContentType.objects.get_for_model(User)
user_assignments = task.assignments.filter(content_type=user_ct)

group_ct = ContentType.objects.get_for_model(Group)
group_assignments = task.assignments.filter(content_type=group_ct)

# Get all tasks assigned to a specific user
user_tasks = Task.objects.filter(
    assignments__content_type=user_ct,
    assignments__object_id=user.id
)
```

## Migration Required

Run migrations to apply the model changes:
```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

## URLs
No changes needed - the existing task URLs continue to work with the updated serializers.
