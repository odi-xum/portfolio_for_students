# AGENTS.md - Guide for Working with Diplom Repository

## Project Overview
This is a Flask web application for managing student achievement portfolios and scholarship requests. The system supports five user roles with different permissions:
- **admin**: User management
- **student**: Submit events for portfolio, request scholarships
- **teacher**: Placeholder dashboard
- **curator**: Review and approve/reject student events
- **commission**: Arbitrate disputed events and make final scholarship decisions

## Essential Commands

### Running the Application
```bash
# Activate virtual environment (if using)
source venv/bin/activate

# Run the Flask development server
python app.py
```
The application runs in debug mode on http://localhost:5000 by default.

### Database Initialization
The database is initialized automatically when running `app.py`:
- Creates tables if they don't exist
- Populates with test data if no admin user exists:
  - admin/admin (password: 111)
  - teacher/teacher (password: 111)
  - student/student (password: 111, group: ИСП-41)
  - curator/curator (password: 111, group: ИСП-41)
  - commission/commission (password: 111)
  - ivanov/ivanov (password: 111, student, group: ИСП-41)
- Creates sample events, notifications, and scholarship requests for testing

### Working with Uploads
- Uploaded files are stored in `./diplom/students/{username}/{event_id}_{title}/`
- Allowed file extensions: png, jpg, jpeg, pdf
- Filenames are sanitized using `secure_filename()`

## Code Organization

### Core Files
- `app.py`: Main Flask application containing routes, authentication, and business logic
- `models.py`: SQLAlchemy model definitions
- `templates/`: HTML templates organized by user role
- `static/`: CSS (`style.css`) and JavaScript files
- `diplom/`: User-uploaded files (created automatically)
- `instance/database.db`: SQLite database file

### User Interface Components
- **Role-based Navigation**: Present in `templates/base.html` as `<nav class="role-nav">`
  - Shows different links based on `current_user.role`
  - Styled in `static/css/style.css` under the "Role-based navigation" section
  - Includes links to role-specific dashboards and relevant actions (e.g., scholarship request for students)
- **Base Template**: `templates/base.html` provides common layout:
  - Authentication check and user info bar
  - Role-based navigation menu
  - Container for flash messages and content blocks
  - Extended by all role-specific templates

### Directory Structure
```
/
├── app.py                 # Flask application entry point
├── models.py              # Database models
├── AGENTS.md              # This file
├── tea_debug.log          # Debug log (auto-generated)
├── txt                    # Unknown purpose file
├── venv/                  # Python virtual environment
├── instance/              # SQLite database
├── static/                # Static assets
│   ├── css/
│   │   └── style.css
│   └── js/
├── templates/             # HTML templates
│   ├── admin.html
│   ├── base.html
│   ├── commission.html
│   ├── curator.html
│   ├── login.html
│   └── student.html
└── diplom/                # User uploads directory
    └── students/
        ├── {username}/
        │   └── {event_id}_{title}/
        │       ├── uploaded files...
```

## Architecture & Data Flow

### Role-Based Access Control
Every route checks `current_user.role` to enforce permissions:
- Admin-only routes: `/admin/*`
- Curator-only routes: `/curator/*`
- Commission-only routes: `/commission/*`
- Student-only routes: `/student/*`
- Teacher routes: `/teacher/*` (currently placeholder)

### Event Lifecycle
1. **Student Submission**: Creates Event with status='pending'
2. **Curator Review**: 
   - Approve: Event.status='approved', adds score
   - Reject: Event.status='disputed', sends to commission
3. **Commission Arbitration** (for disputed events):
   - Confirm rejection: Event.status='rejected'
   - Overrule approve: Event.status='approved'
   - Reconsider: Resets to disputed for re-review

### Scholarship Request Flow
1. Student requests scholarship (requires ≥20 approved events, avg score ≥4.5)
2. Goes to curator for review: status='under_curator_review'
3. Curator forwards to commission: status='under_commission_review'
4. Commission decides: status='approved' or 'rejected'

### Notification System
- Used for cross-role communication
- Curators notified when students submit new events
- Commission members notified when curators reject events
- Notifications stored in database with read/unread status

## Naming Conventions & Style

### Python Code
- Functions and variables: `snake_case`
- Classes: `PascalCase` (User, Event, ScholarshipRequest)
- Constants: `UPPER_CASE` (ALLOWED_EXTENSIONS, BASE_UPLOAD_FOLDER)
- Route functions: Descriptive names matching URL patterns
- Comments: Mixed Russian and English; prioritize understanding code logic over comments

### Templates
- HTML files use Jinja2 templating
- Base template: `base.html` extended by role-specific templates
- Template variables passed explicitly in `render_template()` calls

### Database Models
- Model classes inherit from `db.Model`
- Table names set explicitly with `__tablename__`
- Relationships defined with `db.relationship()` and foreign keys
- Cascading deletes configured where appropriate (`cascade="all, delete-orphan"`)

## Important Gotchas & Non-Obvious Patterns

### Database Initialization
- The `init_test_db()` function runs on every application startup
- It only creates sample data if no admin user exists (checks `User.query.filter_by(username='admin').first()`)
- All test users share the same password hash: `generate_password_hash('111')`
- The upload folder path is set to absolute path: `os.path.abspath('./diplom')`

### File Handling
- Uploaded files are saved to filesystem with secure filenames
- File metadata (path, type) stored in `EventFile` table
- Physical files are NOT deleted when database records are removed (potential cleanup needed)
- File type validation happens via `allowed_file()` checking extension against `ALLOWED_EXTENSIONS`

### Query Optimization
- Uses `joinedload()` for eager loading to prevent N+1 queries in dashboard views
- Example: `Event.query.options(joinedload(Event.student))` loads student data with events

### Status Fields & State Management
- Events have multiple status-tracking fields:
  - `status`: Current workflow state
  - `previous_status`: Stores status before commission review (for reconsideration)
  - `commission_reviewed_at`: Timestamp for filtering commission-reviewed items
- Scholarship requests track review stages with `status` and `commission_reviewed_at`

### Time Handling
- All timestamps use `datetime.utcnow()` for consistency
- No timezone conversion applied in displayed times

### Security Notes
- Passwords hashed with Werkzeug's `generate_password_hash`
- Session management via Flask-Login
- CSRP protection not visibly implemented (consider adding for production)
- File uploads restricted by extension but not content-type validated

## Testing Approach

### Implicit Testing
- The application includes built-in test data generation
- Manual testing via running the application and navigating role-specific dashboards
- No automated test suite visible in repository

### Test Data Characteristics
- 20 approved events with score=5 created for 'student' user to satisfy scholarship requirements
- Additional test data for each workflow stage:
  - 5 pending events (curator review)
  - 5 disputed events (commission arbitration)
  - 3 resolved events (commission archive)
  - Scholarship requests in various states

## Development Guidelines

### Adding New Features
1. Add model changes to `models.py` if needed
2. Implement routes in `app.py` with appropriate `@login_required` and role checks
3. Create/update templates in `templates/` directory
4. Update navigation if needed (currently implicit through direct URL access)
5. Consider adding notifications for cross-role awareness

### Database Changes
- Modify models in `models.py`
- The application uses Flask-SQLAlchemy; migrations not visibly configured
- For production, consider adding Flask-Migrate or similar
- Test database changes by removing `instance/database.db` and restarting app

### Static Assets
- CSS: Modify `static/css/style.css`
- JavaScript: Add to `static/js/` and reference in templates
- Template inheritance: Extend `base.html` and override content blocks

## Troubleshooting

### Common Issues
- **Database locked errors**: Ensure only one Flask instance running
- **Missing upload directories**: The app creates them automatically, but check permissions
- **Role access denied**: Verify user role in database matches route expectations
- **File upload failures**: Check file extension against ALLOWED_EXTENSIONS

### Debugging
- Run with `debug=True` (already set in app.py)
- Check `tea_debug.log` for debug output
- Use Flask debugger when errors occur (development only)
- SQLAlchemy query logging can be enabled if needed

## Deployment Considerations
- Change SECRET_KEY in production
- Use production WSGI server (Gunicorn, uWSGI) instead of Flask development server
- Consider PostgreSQL/MySQL instead of SQLite for production
- Set up proper logging and error monitoring
- Implement CSRF protection
- Add rate limiting on authentication endpoints
- Configure secure headers and HTTPS
