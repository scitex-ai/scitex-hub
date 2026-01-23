# SciTeX Visitor Pool Architecture

## Overview

The SciTeX Visitor Pool system provides secure, isolated temporary access to the platform for visitor users without requiring account creation. This document explains how visitor slots are allocated, how data is separated between visitors, and the security model.

## Architecture Summary

- **Pool Size**: 4 pre-allocated visitor accounts
- **Session Duration**: 1 hour per visitor
- **Daily Capacity**: Up to 96 visitors per day (4 slots × 24 hours)
- **Data Migration**: Automatic transfer to permanent account on signup
- **Isolation Level**: Complete workspace and session separation

## Visitor Account Structure

### Pre-allocated Accounts

The system maintains 4 Django user accounts:
- `visitor-001` through `visitor-004`
- Each has a dedicated filesystem workspace
- Each has a default project: `default-project-001` through `default-project-004`

### Account Locations
```
data/users/visitor-001/
data/users/visitor-002/
data/users/visitor-003/
data/users/visitor-004/
```

## Allocation Mechanism

### 1. Slot Assignment Process

When a visitor requests access:

```python
# apps/project_app/services/visitor_pool.py
def allocate_visitor_slot(request):
    """
    1. Find first available slot (visitor_number 1-4)
    2. Check if slot is free (no active allocation)
    3. Create VisitorAllocation record with:
       - visitor_number (1-4)
       - allocation_token (32-byte secure random token)
       - expires_at (current_time + 1 hour)
       - is_active = True
    4. Store in session:
       - visitor_allocation_token
       - visitor_user_id
       - visitor_project_id
    5. Return allocated visitor account and project
    """
```

### 2. Session-Based Security

**Key Session Variables**:
```python
SESSION_KEY_ALLOCATION_TOKEN = "visitor_allocation_token"  # 32-byte random token
SESSION_KEY_VISITOR_ID = "visitor_user_id"                 # visitor-00X user ID
SESSION_KEY_PROJECT_ID = "visitor_project_id"              # default-project-00X ID
```

**Security Model**:
- Each visitor gets a unique allocation token (cryptographically random)
- Token is required to access the allocated slot
- Token is stored only in the visitor's session (HttpOnly cookie)
- Different visitors cannot access each other's tokens

## Data Separation & Isolation

### 1. Filesystem Isolation

Each visitor account has a completely separate filesystem workspace:

```
data/users/visitor-001/
├── scholar/              # Visitor 1's scholar data
│   ├── papers/
│   └── bibliographies/
├── writer/               # Visitor 1's writer data
│   ├── documents/
│   └── figures/
├── code/                 # Visitor 1's code data
└── visualizations/       # Visitor 1's viz data

data/users/visitor-002/   # Completely separate for Visitor 2
├── scholar/
├── writer/
├── code/
└── visualizations/
```

**Isolation Guarantee**: The SciTeX core library uses the Django user ID to construct file paths. Since each visitor is assigned a different user account (visitor-001 vs visitor-002), they cannot physically access each other's files.

### 2. Database Isolation

**Project Ownership**:
```python
class Project(models.Model):
    owner = models.ForeignKey(User)  # visitor-001, visitor-002, etc.
    # Each project is owned by exactly one visitor account
```

**Django ORM Filtering**:
```python
# Only returns projects owned by the current visitor account
Project.objects.filter(owner=request.user)
```

Since Django authentication identifies each visitor as a different user (`visitor-001` vs `visitor-002`), database queries automatically filter to only their owned data.

### 3. Session Isolation

**Session Storage**: Django sessions are keyed by session cookie
- Visitor A's session: `sessionid=abc123...` → allocation_token=token_A
- Visitor B's session: `sessionid=xyz789...` → allocation_token=token_B

**Cross-Session Protection**:
- Session cookies are HttpOnly (not accessible via JavaScript)
- Session cookies are Secure (only transmitted over HTTPS in production)
- Different browsers/tabs get different session IDs
- Expired sessions are automatically cleared

## Visitor Journey Flow

### Typical User Flow

```
1. User arrives at SciTeX
   ↓
2. Views /visitor-status/ (optional)
   → Shows all 4 slots' current status
   → No allocation created yet
   ↓
3. Navigates to /scholar/, /writer/, /code/, or /viz/
   → Triggers visitor slot allocation
   → Session stores allocation_token
   → User is now assigned to visitor-00X
   ↓
4. Returns to /visitor-status/
   → Now sees 1 allocated slot (theirs) + 3 free/allocated
   → Can see their expiration countdown
   ↓
5. Works on projects for up to 60 minutes
   ↓
6. Either:
   a) Signs up → data migrated, slot freed
   b) Session expires → slot freed, data deleted
```

### Why /visitor-status/ Doesn't Require Allocation

The visitor status page is designed to be accessible **before** allocation:
- Users can check if slots are available before starting
- Users can learn about the system without commitment
- Transparent visibility of pool congestion

**Result**: When you first visit `/visitor-status/`, you see all slots' actual status, which may be "all free" if no one else is using the system.

## Slot Lifecycle

### 1. Allocation (T+0)

```
Visitor arrives → allocate_visitor_slot() → VisitorAllocation created
├── visitor_number: 2
├── allocation_token: "a3f9c8d2e1b4..."
├── expires_at: T+1hour
├── is_active: True
└── Session stores: allocation_token, visitor_user_id, visitor_project_id
```

### 2. Active Session (T+0 to T+1h)

```
Every request:
1. Load allocation_token from session
2. Verify VisitorAllocation exists and is_active=True
3. Check expires_at > now()
4. Authenticate as visitor-00X user
5. All data operations scoped to that user
```

### 3. Expiration (T+1h)

```
Automatic cleanup:
1. expires_at reached → slot becomes available
2. Next visitor can claim the same visitor_number
3. Previous visitor's work remains in database until migration or manual cleanup
4. Expired sessions redirect to signup page with data migration offer
```

### 4. Data Migration on Signup

When a visitor creates an account:

```python
# apps/project_app/services/visitor_pool.py
def claim_project_on_signup(visitor_allocation_token, new_user):
    """
    1. Find VisitorAllocation by token
    2. Get visitor's default project
    3. Transfer project ownership:
       project.owner = new_user  # visitor-002 → real-user
    4. Transfer all project data (files remain at old path but are accessible)
    5. Create symbolic links or migrate files to new user workspace
    6. Mark allocation as inactive (frees the slot)
    7. Clear visitor session variables
    """
```

**Migration Guarantee**: All work done in visitor mode is preserved and transferred to the new account.

## Security Model

### Threat Model & Mitigations

#### 1. **Cross-Visitor Data Access**
**Threat**: Visitor A tries to access Visitor B's data
**Mitigation**:
- Different user accounts (visitor-001 vs visitor-002)
- Django authentication enforces user-based filtering
- Filesystem paths include user ID (cannot traverse to other users)
- Database queries automatically filtered by `request.user`

#### 2. **Session Hijacking**
**Threat**: Attacker steals visitor's session cookie
**Mitigation**:
- HttpOnly cookies (not accessible via JavaScript/XSS)
- Secure flag in production (HTTPS only)
- 1-hour session lifetime limits exposure window
- Allocation token required (32-byte random, stored only in session)

#### 3. **Slot Exhaustion (DoS)**
**Threat**: Malicious actors consume all 4 slots
**Mitigation**:
- 1-hour automatic expiration ensures slot rotation
- 4 slots support 96 visitors/day (sufficient for initial load)
- Can increase POOL_SIZE if needed
- Future: Rate limiting by IP address

#### 4. **Data Persistence After Expiration**
**Threat**: Visitor data remains accessible after session expires
**Mitigation**:
- Expired allocations cannot be used (expires_at check)
- Data remains in database but is inaccessible (no authentication)
- Visitor cannot log in directly (no password set)
- Only way to access: migration to permanent account via signup

#### 5. **Visitor Account Direct Login**
**Threat**: Someone discovers visitor-001 credentials and logs in directly
**Mitigation**:
- Visitor accounts have no passwords (cannot use Django login form)
- Access only via allocation token in session
- No public credential exposure

## Implementation Files

### Core Logic
- `apps/project_app/services/visitor_pool.py` - Allocation and migration logic
- `apps/project_app/models.py` - VisitorAllocation model
- `apps/project_app/middleware.py` - Visitor authentication middleware

### User Interface
- `templates/global_base_partials/global_header.html` - Countdown timer
- `apps/public_app/views.py` - visitor_status() view (lines 626-709)
- `apps/public_app/templates/public_app/visitor_status.html` - Status page

### Configuration
- `apps/project_app/context_processors.py` - visitor_expiration_context()
- `config/settings/settings_shared.py` - Context processor registration

## Pool Status Monitoring

### Real-Time Status Page

URL: `/visitor-status/`

**Public Information Shown**:
- Total slots (4)
- Allocated slots (currently in use)
- Available slots (free)
- Expiration times in minutes (without identifying which visitor)

**Private Information Hidden**:
- Visitor usernames (visitor-001, etc.)
- Allocation tokens
- User activities
- File contents or project details

**For Current Visitor**:
- Personal countdown timer showing remaining session time
- Color-coded warnings (green > 15m, orange > 5m, red < 5m)
- Clear call-to-action to sign up and migrate data

### Pool Status Query

```python
from apps.project_app.services.visitor_pool import VisitorPool

status = VisitorPool.get_pool_status()
# Returns: {
#     "total": 4,
#     "allocated": 2,
#     "free": 2,
#     "expired": 0
# }
```

## Data Migration Process

### Automatic Migration on Signup

1. **Visitor completes signup form** → creates new User account
2. **Signup view calls**:
   ```python
   VisitorPool.claim_project_on_signup(
       visitor_allocation_token=request.session.get("visitor_allocation_token"),
       new_user=newly_created_user
   )
   ```
3. **Migration executes**:
   - Finds visitor's default project
   - Changes `project.owner` from visitor-00X to new user
   - All related data (papers, documents, figures) transfers via foreign keys
   - Files remain accessible (Django ORM handles ownership)
   - Visitor session cleared, slot freed for next visitor

### Verification

After migration, the new user sees:
- All projects created in visitor mode
- All documents, papers, bibliographies
- All figures, code, visualizations
- Complete history preserved

The freed visitor slot becomes available immediately for the next visitor.

## Advantages of This Architecture

### 1. **True Isolation**
- Uses Django's built-in user system (battle-tested)
- No custom permission logic needed
- Filesystem and database automatically isolated

### 2. **Seamless Migration**
- One database update (change project owner)
- No file copying needed
- Zero data loss
- Instant transfer

### 3. **Automatic Cleanup**
- Time-based expiration (no cron jobs needed)
- Self-rotating pool
- No manual intervention required

### 4. **Scalability**
- Easy to increase pool size (change POOL_SIZE constant)
- Stateless allocation (any server can handle any visitor)
- Session-based (works with load balancers)

### 5. **Security**
- Cryptographically random tokens
- No shared secrets
- Standard Django session security
- Clear separation boundaries

## Future Enhancements

### Short-Term
- [ ] Rate limiting by IP address (prevent abuse)
- [ ] Automatic cleanup of abandoned visitor data after 7 days
- [ ] Analytics dashboard for pool utilization

### Long-Term
- [ ] Dynamic pool sizing based on demand
- [ ] Redis-based session storage for multi-server deployments
- [ ] Visitor activity tracking (anonymized)
- [ ] A/B testing signup conversion rates vs session duration

## Conclusion

The SciTeX Visitor Pool provides secure, isolated temporary access through:
1. **Pre-allocated accounts** with dedicated workspaces
2. **Session-based allocation** with cryptographic tokens
3. **Complete data isolation** via Django user model
4. **Automatic expiration** and slot rotation
5. **Seamless data migration** to permanent accounts

This architecture balances user experience (no signup friction), security (complete isolation), and operational efficiency (automatic cleanup and rotation).
