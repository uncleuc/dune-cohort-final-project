# PyChat

A real-time chat application scaffold built with Django and Django Channels.

## Current Status

- Django project scaffolded in `PyChat/`
- `chat` app created with models, admin, and consumers
- Channels integration configured for WebSocket real-time messaging
- User authentication (login, logout, register)
- Chat conversation management (create, list, view)
- Message persistence and real-time updates via WebSockets
- Admin-only REST API endpoints under `/api/` with Token Auth and JWT support
- Conversation list filter chips now control All / Unread / Favorites / Groups visibility
- Database migrations applied

## Project Structure

- `PyChat/` - Django project settings, ASGI configuration, and project URLs
- `PyChat/accounts/` - User account management (registration, login, profile, settings)
- `PyChat/chat/` - Chat application models, admin, routing, consumers, views, and templates
- `.venv/` - Python virtual environment

### App Organization

**Accounts App** (`accounts/`)
- User registration, login/logout
- User profile and account settings
- Account-related views and templates

**Chat App** (`chat/`)
- Real-time messaging via WebSockets
- Conversation and message models
- Friend system and blocking functionality
- Chat views and consumer classes
- Chat-related templates

Additional files and templates:

- `PyChat/accounts/templates/accounts/` - Account management templates (register, login, profile, settings)
- `PyChat/chat/templates/chat/` - Chat-related templates (conversation list, detail, friends, etc.)
- `PyChat/chat/models.py` — Conversation, Message, FriendRequest, Block, and Presence models
- `PyChat/chat/consumers.py` — WebSocket consumers for real-time chat and notifications with presence tracking
- `PyChat/chat/routing.py` — WebSocket URL routing configuration

## Documentation Policy

All future changes, features, and new files will be documented in this README under the appropriate section.

### Change Log

- **2026-05-26**: Reorganized user account management into dedicated `accounts` app; moved register, login, logout, profile, and settings views and templates from `chat` to `accounts`; updated URL routing to use namespace for account URLs
- **2026-05-24**: Added WhatsApp-style two-column layout with collapsible icon sidebar; created friends, profile, and settings pages; wired sidebar links
- **2026-05-24**: Reworked conversation list into left-side panel with conversation preview/selection behavior
- **2026-05-24**: Added file upload endpoint (`upload_attachment`) and attachment metadata broadcasting for real-time rendering
- **2026-05-24**: Updated conversation detail view with attachment uploads, WebSocket fallback polling, and attachment link display
- **2026-05-24**: Added development media serving for attachments when `DEBUG=True`
- **2026-05-11**: Initialized Django project and created `chat` app with models, admin, views, and WebSocket consumers
- **2026-05-11**: Generated initial database migrations
- **2026-05-11**: Added user authentication system (register, login, logout)
- **2026-05-11**: Created base template with Bootstrap 5 styling and responsive navbar
- **2026-05-11**: Implemented conversation and message management with real-time updates via WebSockets

## Technical Compliance Audit

### Completed features
- Real-time chat with Django Channels and WebSockets
- DB-backed message persistence and attachment uploads
- User registration, login, logout, and protected chat views
- Friend system, direct conversation creation, and group chat creation
- Conversation list ordering by latest activity and live unread badge updates
- Conversation filters now work for All / Unread / Favorites / Groups
- Admin-only REST API endpoints, Token Auth, and JWT support under `/api/`
- `api_docs.md` added for the API endpoints
- Channel layer configured with `InMemoryChannelLayer` for local development
- Django system checks pass with `manage.py check`

### Remaining tasks (next steps)
- Add automated tests for chat views, models, consumers, and notification flows
- Add production-grade environment variables and deployment checks for Render
- Optionally add Redis-backed channel layers for multi-worker production use
- Verify final admin/API permissions against the course rubric

## Next Steps

1. Add automated tests for project business logic and websocket flows
2. Create a dependency manifest such as `requirements.txt`
3. Harden the deployment config for production (Redis, env variables, static/media setup)
4. Confirm whether a REST API / DRF integration is required by the course rubric
5. Clean up unused apps or register the `accounts` app if it is intended to be part of the final project


Add deployment documentation and a clear startup guide for the application environment

## Next Steps

1. Add automated tests for project business logic and websocket flows
2. Create a dependency manifest such as `requirements.txt`
3. Harden the deployment config for production (Redis, env variables, static/media setup)
4. Confirm whether a REST API / DRF integration is required by the course rubric# dune-cohort-final-project
# dune-cohort-final-project
