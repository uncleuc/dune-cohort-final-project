# API Overview

## Authentication
- Token auth: POST /api/token-auth/ with username and password
- JWT: POST /api/token/ with username and password
- Refresh JWT: POST /api/token/refresh/

## Admin account endpoints
- GET /api/accounts/ — list users
- POST /api/accounts/ — create a user
- GET /api/accounts/<username>/ — retrieve a user
- PUT/PATCH /api/accounts/<username>/ — update a user
- DELETE /api/accounts/<username>/ — delete a user
- GET /api/accounts/me/ — current admin user

All account endpoints require admin authentication.
