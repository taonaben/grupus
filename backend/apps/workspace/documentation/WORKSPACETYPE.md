# Workspace Type System

## Overview

The Workspace Type system provides a hybrid approach to workspace customization, allowing developers to define validated schemas for different workspace purposes (e.g., courses, hackathons, bootcamps) while preventing users from adding arbitrary custom fields.

## Key Features

- **Developer-Controlled Schemas**: Define workspace types with specific field requirements
- **Runtime Validation**: Metadata is validated against the workspace type schema without requiring database migrations
- **Type Safety**: Supports multiple field types with validation
- **Required Fields**: Enforce mandatory fields for each workspace type
- **No Custom Fields**: Users cannot add fields outside the defined schema

## Architecture

### Models

#### WorkspaceType
```python
class WorkspaceType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    schema = models.JSONField(default=dict, blank=True, null=True)
```

#### Workspace
```python
class Workspace(models.Model):
    # ... other fields
    workspace_type = models.ForeignKey(
        "WorkspaceType",
        on_delete=models.PROTECT,
        related_name="workspaces",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True, null=True)
```

## Schema Definition

### Supported Field Types

- `string` - Text values
- `number` - Integer or float values
- `boolean` - True/false values
- `user` - User ID reference (validated as string UUID)
- `array` - List of values
- `object` - Nested JSON objects
- `date` - Date values

### Schema Structure

```json
{
  "fields": {
    "<field_name>": {
      "type": "<field_type>",
      "required": true|false
    }
  }
}
```

## Usage Examples

### 1. Course Workspace Type

**Create WorkspaceType:**
```json
{
  "name": "course",
  "schema": {
    "fields": {
      "course_code": {
        "type": "string",
        "required": true
      },
      "semester": {
        "type": "string",
        "required": true
      },
      "credits": {
        "type": "number",
        "required": false
      },
      "lecturer": {
        "type": "user",
        "required": true
      },
      "department": {
        "type": "string",
        "required": false
      }
    }
  }
}
```

**Create Workspace:**
```json
{
  "name": "CS101 Spring 2026",
  "description": "Introduction to Computer Science",
  "workspace_type": "<workspace_type_id>",
  "metadata": {
    "course_code": "CS101",
    "semester": "Spring 2026",
    "credits": 3,
    "lecturer": "uuid-of-lecturer",
    "department": "Computer Science"
  }
}
```

### 2. Hackathon Workspace Type

**Create WorkspaceType:**
```json
{
  "name": "hackathon",
  "schema": {
    "fields": {
      "event_date": {
        "type": "date",
        "required": true
      },
      "max_team_size": {
        "type": "number",
        "required": true
      },
      "prizes": {
        "type": "array",
        "required": false
      },
      "sponsors": {
        "type": "array",
        "required": false
      },
      "registration_deadline": {
        "type": "date",
        "required": true
      },
      "theme": {
        "type": "string",
        "required": false
      }
    }
  }
}
```

**Create Workspace:**
```json
{
  "name": "Spring Hack 2026",
  "workspace_type": "<workspace_type_id>",
  "metadata": {
    "event_date": "2026-04-15",
    "max_team_size": 5,
    "prizes": ["$5000", "$2000", "$1000"],
    "sponsors": ["TechCorp", "StartupX"],
    "registration_deadline": "2026-04-01",
    "theme": "AI for Good"
  }
}
```

### 3. Bootcamp Workspace Type

**Create WorkspaceType:**
```json
{
  "name": "bootcamp",
  "schema": {
    "fields": {
      "program_duration_weeks": {
        "type": "number",
        "required": true
      },
      "start_date": {
        "type": "date",
        "required": true
      },
      "end_date": {
        "type": "date",
        "required": true
      },
      "instructors": {
        "type": "array",
        "required": true
      },
      "curriculum": {
        "type": "object",
        "required": false
      },
      "certification": {
        "type": "boolean",
        "required": false
      }
    }
  }
}
```

**Create Workspace:**
```json
{
  "name": "Full Stack Web Development Bootcamp",
  "workspace_type": "<workspace_type_id>",
  "metadata": {
    "program_duration_weeks": 12,
    "start_date": "2026-03-01",
    "end_date": "2026-05-24",
    "instructors": ["user-id-1", "user-id-2"],
    "curriculum": {
      "weeks_1_4": "Frontend Fundamentals",
      "weeks_5_8": "Backend Development",
      "weeks_9_12": "Full Stack Projects"
    },
    "certification": true
  }
}
```

## Validation

### Automatic Validation

The `WorkspaceSerializer` automatically validates metadata against the workspace type schema during workspace creation or updates:

1. **Required Fields Check**: Ensures all required fields are present
2. **Extra Fields Check**: Rejects any fields not defined in the schema
3. **Type Validation**: Validates that each field matches its specified type

### Validation Errors

Examples of validation errors:

```json
// Missing required field
{
  "metadata": [
    "Required field 'course_code' is missing."
  ]
}

// Invalid field type
{
  "metadata": [
    "Field 'credits' must be a number."
  ]
}

// Extra field not in schema
{
  "metadata": [
    "Field 'custom_field' is not allowed for this workspace type."
  ]
}
```

## API Endpoints

### Create WorkspaceType
```
POST /api/workspace-types/
Content-Type: application/json

{
  "name": "course",
  "schema": { ... }
}
```

### Update WorkspaceType
```
PATCH /api/workspace-types/<id>/
Content-Type: application/json

{
  "schema": { ... }
}
```

### Create Workspace with Type
```
POST /api/workspaces/
Content-Type: application/json

{
  "name": "My Workspace",
  "workspace_type": "<workspace_type_id>",
  "metadata": { ... }
}
```

### Update Workspace Metadata
```
PATCH /api/workspaces/<id>/
Content-Type: application/json

{
  "metadata": { ... }
}
```

## Migration Guide

### Database Migration

After implementing these changes, create and run migrations:

```bash
# Create migration
python manage.py makemigrations workspace

# Review the migration file
# The system will detect the change from CharField to ForeignKey

# Apply migration
python manage.py migrate workspace
```

### Handling Existing Data

If you have existing workspaces with `workspace_type` as a string:

1. Create WorkspaceType objects for existing types
2. Create a data migration to convert string values to ForeignKey references
3. Update existing workspaces to use the new ForeignKey

Example data migration:
```python
from django.db import migrations

def convert_workspace_types(apps, schema_editor):
    Workspace = apps.get_model('workspace', 'Workspace')
    WorkspaceType = apps.get_model('workspace', 'WorkspaceType')
    
    # Create default workspace types
    generic_type = WorkspaceType.objects.create(name='generic', schema={})
    
    # Update existing workspaces
    for workspace in Workspace.objects.all():
        if workspace.workspace_type == 'generic':
            workspace.workspace_type = generic_type
            workspace.save()

class Migration(migrations.Migration):
    dependencies = [
        ('workspace', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(convert_workspace_types),
    ]
```

## Best Practices

### 1. Schema Design

- Keep schemas simple and focused
- Use clear, descriptive field names
- Set `required: true` only for truly mandatory fields
- Document expected formats for complex fields

### 2. WorkspaceType Naming

- Use lowercase, singular names: `course`, `hackathon`, `bootcamp`
- Keep names short and memorable
- Use underscores for multi-word types: `study_group`

### 3. Metadata Organization

- Store only workspace-type-specific data in metadata
- Use common Workspace model fields for shared attributes
- Keep metadata flat when possible
- Use nested objects only when logically grouped

### 4. Validation

- Always validate metadata before saving
- Provide clear error messages
- Handle optional fields gracefully
- Consider default values for common optional fields

## Extending the System

### Adding New Field Types

To add a new field type, update the `validate_data()` method in the WorkspaceType model:

```python
def validate_data(self, data):
    # ... existing code
    
    # Add custom type validation
    elif field_type == "email":
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            errors.append(f"Field '{field_name}' must be a valid email.")
```

### Adding Field Constraints

Extend the schema to support additional validation rules:

```json
{
  "fields": {
    "age": {
      "type": "number",
      "required": true,
      "min": 0,
      "max": 120
    },
    "username": {
      "type": "string",
      "required": true,
      "minLength": 3,
      "maxLength": 50,
      "pattern": "^[a-zA-Z0-9_]+$"
    }
  }
}
```

## Troubleshooting

### Common Issues

**Issue**: Validation errors when creating workspace
- **Solution**: Check that all required fields are present and match the correct type

**Issue**: Cannot add custom field to workspace
- **Solution**: This is by design. Custom fields must be added to the WorkspaceType schema first

**Issue**: Migration fails with existing data
- **Solution**: Create a data migration to handle the CharField to ForeignKey conversion

**Issue**: WorkspaceType cannot be deleted
- **Solution**: Due to `on_delete=models.PROTECT`, you must migrate or delete all workspaces using this type first

## Security Considerations

1. **Type Safety**: Schema validation prevents injection of arbitrary data structures
2. **Access Control**: Implement appropriate permissions for WorkspaceType creation/modification
3. **User References**: Validate that user IDs in metadata actually exist and are accessible
4. **Schema Changes**: Be cautious when modifying schemas for existing workspace types

## Performance

- Validation occurs at the serializer level before database operations
- JSON field indexing can be added for frequently queried metadata fields
- Consider caching WorkspaceType schemas for high-traffic scenarios

```python
# Example: Add GIN index for metadata field queries (PostgreSQL)
class Workspace(models.Model):
    # ... fields
    
    class Meta:
        indexes = [
            models.Index(fields=['metadata'], name='workspace_metadata_idx', opclasses=['jsonb_path_ops'])
        ]
```
