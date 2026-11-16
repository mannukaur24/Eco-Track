# Database Design – EcoTrack

## 1. Design Principles

- Relational model implemented with Flask-SQLAlchemy ORM and MySQL 8.
- Primary keys on all tables; foreign keys with `ON DELETE` behaviour to preserve referential integrity.
- Indexes on frequently queried columns (`email`, `category_name`, `status`, foreign keys).
- Timestamps (`created_at`, `updated_at`) stored in UTC.
- Status fields use constrained string values with defined transitions (see Section 5).

## 2. Entity Dictionary

### Users
| Attribute | Type | Null | Key | Description |
|-----------|------|------|-----|-------------|
| id | INT | NO | PK | Surrogate primary key |
| full_name | VARCHAR(120) | NO | | Citizen/staff/admin full name |
| email | VARCHAR(120) | NO | UK | Unique login email (lowercased) |
| password_hash | VARCHAR(255) | NO | | Salted hash (Werkzeug/bcrypt) |
| role | VARCHAR(20) | NO | | `Citizen`, `Administrator`, or `Staff` |
| phone | VARCHAR(20) | YES | | Contact phone |
| is_active | BOOLEAN | NO | | Account active flag |
| created_at | DATETIME | NO | | Record creation timestamp (UTC) |
| updated_at | DATETIME | NO | | Record last-update timestamp (UTC) |

Relationships: one User may submit many Reports; one User may have one Staff profile; one User may be assigned many CollectionTasks (as staff); one User may assign many CollectionTasks (as assigning admin); one User may author many TaskUpdates.

### Staff
| Attribute | Type | Null | Key | Description |
|-----------|------|------|-----|-------------|
| id | INT | NO | PK | Surrogate primary key |
| user_id | INT | NO | UK, FK → Users.id | Link to user account |
| availability | VARCHAR(50) | YES | | Staff availability note |
| service_area | VARCHAR(120) | YES | | Geographic service area |

Relationship: one-to-one with Users (a staff member is a user with role `Staff`).

### Waste_Categories
| Attribute | Type | Null | Key | Description |
|-----------|------|------|-----|-------------|
| id | INT | NO | PK | Surrogate primary key |
| category_name | VARCHAR(80) | NO | UK | e.g. Organic Waste, Plastic Waste |
| description | TEXT | YES | | Category description |

Relationship: one category may be referenced by many Reports.

### Locations
| Attribute | Type | Null | Key | Description |
|-----------|------|------|-----|-------------|
| id | INT | NO | PK | Surrogate primary key |
| address_text | VARCHAR(255) | NO | | Human-readable address |
| latitude | FLOAT | YES | | Map latitude |
| longitude | FLOAT | YES | | Map longitude |

Relationship: one location may be referenced by many Reports.

### Reports
| Attribute | Type | Null | Key | Description |
|-----------|------|------|-----|-------------|
| id | INT | NO | PK | Surrogate primary key |
| user_id | INT | NO | FK → Users.id | Citizen who submitted |
| category_id | INT | YES | FK → Waste_Categories.id | Selected waste category |
| location_id | INT | YES | FK → Locations.id | Reported location |
| description | TEXT | NO | | Complaint description |
| image_path | VARCHAR(255) | YES | | Stored upload path |
| rejection_reason | TEXT | YES | | Reason given when a report is rejected |
| status | VARCHAR(20) | NO | | `Pending`, `Verified`, `Rejected`, `Assigned`, `In Progress`, `Completed` |
| reference | VARCHAR(20) | NO | UK | Unique report reference |
| created_at | DATETIME | NO | | Submission timestamp |
| updated_at | DATETIME | NO | | Last status update timestamp |

Relationships: belongs to one User, one Waste_Category, one Location; may generate many CollectionTasks.

### Collection_Tasks
| Attribute | Type | Null | Key | Description |
|-----------|------|------|-----|-------------|
| id | INT | NO | PK | Surrogate primary key |
| report_id | INT | NO | FK → Reports.id | Source report |
| staff_id | INT | YES | FK → Users.id | Assigned collection staff |
| assigned_by | INT | YES | FK → Users.id | Administrator who assigned |
| due_date | DATETIME | YES | | Target completion date |
| task_status | VARCHAR(20) | NO | | `Assigned`, `In Progress`, `Completed`, `Overdue` |
| instructions | TEXT | YES | | Assignment instructions |
| completed_at | DATETIME | YES | | Completion timestamp |
| created_at | DATETIME | NO | | Task creation timestamp |
| updated_at | DATETIME | NO | | Task last-update timestamp (UTC) |

Relationships: belongs to one Report; assigned to one Staff user; assigned by one Administrator user; has many TaskUpdates.

### Task_Updates
| Attribute | Type | Null | Key | Description |
|-----------|------|------|-----|-------------|
| id | INT | NO | PK | Surrogate primary key |
| task_id | INT | NO | FK → Collection_Tasks.id | Parent task |
| updated_by | INT | YES | FK → Users.id | Staff member recording update |
| status | VARCHAR(20) | NO | | Status at time of update |
| remarks | TEXT | YES | | Staff remarks |
| created_at | DATETIME | NO | | Update timestamp |

### Awareness_Articles
| Attribute | Type | Null | Key | Description |
|-----------|------|------|-----|-------------|
| id | INT | NO | PK | Surrogate primary key |
| title | VARCHAR(200) | NO | | Article title |
| content | TEXT | NO | | Article body |
| topic | VARCHAR(100) | YES | | e.g. Segregation, Recycling |
| is_published | BOOLEAN | NO | | Publication flag |
| published_at | DATETIME | YES | | Publication timestamp |
| created_at | DATETIME | NO | | Creation timestamp |
| updated_at | DATETIME | NO | | Last edit timestamp |

## 3. Relationships and Cardinality

| Relationship | Cardinality | FK |
|--------------|-------------|----|
| Users → Reports | 1:N | Reports.user_id |
| Users → Staff | 1:0..1 | Staff.user_id |
| Users → Collection_Tasks (assigned) | 1:N | Collection_Tasks.staff_id |
| Users → Collection_Tasks (assigned by) | 1:N | Collection_Tasks.assigned_by |
| Users → Task_Updates | 1:N | Task_Updates.updated_by |
| Waste_Categories → Reports | 1:N | Reports.category_id |
| Locations → Reports | 1:N | Reports.location_id |
| Reports → Collection_Tasks | 1:N | Collection_Tasks.report_id |
| Collection_Tasks → Task_Updates | 1:N | Task_Updates.task_id |

### Delete behaviour
- `Users → Staff`: `CASCADE` (deleting a user removes the staff profile).
- `Users → Reports`: `CASCADE` (reports owned by a deleted user are removed).
- `Reports → Collection_Tasks`: `CASCADE` (deleting a report removes its tasks).
- `Collection_Tasks → Task_Updates`: `CASCADE` (deleting a task removes its updates).
- `Waste_Categories → Reports`: `SET NULL` (reports keep their category reference nullable if a category is removed).
- `Locations → Reports`: `SET NULL`.
- `Users → Collection_Tasks` (staff / assigned_by): `SET NULL`.

## 4. Indexes

- `users.email` (unique)
- `waste_categories.category_name` (unique)
- `reports.reference` (unique)
- `reports.status`
- `reports.user_id`
- `collection_tasks.staff_id`
- `collection_tasks.task_status`
- `task_updates.task_id`

## 5. Status Definitions and Transitions

### Report lifecycle
| Status | Meaning | Valid transitions from |
|--------|---------|------------------------|
| `Pending` | Awaiting administrator review | — (initial on creation) |
| `Verified` | Reviewed and approved | `Pending` |
| `Rejected` | Rejected with reason (terminal) | `Pending`, `Verified` |
| `Assigned` | Task assigned to staff | `Verified` |
| `In Progress` | Staff actively collecting | `Assigned` |
| `Completed` | Collection finished | `In Progress`, `Assigned` |

### Task lifecycle
| Status | Meaning | Valid transitions from |
|--------|---------|------------------------|
| `Assigned` | Task created and assigned to staff | — (initial on creation) |
| `In Progress` | Staff started work | `Assigned` |
| `Completed` | Work finished | `Assigned`, `In Progress` |
| `Overdue` | `due_date` passed without completion | Computed from `Assigned`/`In Progress` when due date lapses |

### Audit requirements
Important status changes and task assignments store the responsible account (`updated_by`, `assigned_by`) and timestamp (`created_at`, `completed_at`, `updated_at`) to support accountability and troubleshooting (synopsis §6 backup/audit).

## 6. Data Integrity and Constraints

- Entity integrity: every table has a primary key.
- Referential integrity: foreign keys enforced by InnoDB; cascade/set-null rules above.
- Domain integrity: `role`, `status`, `task_status`, `is_published` constrained to allowed values; `email` unique; `reference` unique; `category_name` unique.
- Required fields enforced at ORM level (`nullable=False`) and by server-side form validation.
- Image uploads validated by type/size at the application layer (not a DB constraint).
