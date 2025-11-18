# Authentication System Setup & Testing Guide

## Overview
InboxHub CRM now includes a complete JWT-based authentication system protecting all sensitive API endpoints and frontend routes.

---

## Environment Setup

### Backend Configuration

1. Create or update `/backend/.env` with the following required variables:

```bash
# Existing MongoDB config
MONGO_URL=mongodb://localhost:27017
DB_NAME=inboxhub_crm
CORS_ORIGINS=http://localhost:3000

# NEW: Authentication Configuration (REQUIRED)
AUTH_SECRET_KEY=your-secret-key-must-be-at-least-32-characters-long-change-this
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**⚠️ IMPORTANT:**
- `AUTH_SECRET_KEY` must be at least 32 characters for production use
- Generate a strong random key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Never commit the actual secret key to version control

### Frontend Configuration

No additional configuration needed. The frontend already uses `REACT_APP_BACKEND_URL` from your existing setup.

---

## Installation

### Backend Dependencies

All required packages are already in `requirements.txt`:
- `passlib[bcrypt]` - Password hashing
- `python-jose[cryptography]` - JWT token management

If you need to install:
```bash
cd backend
pip install -r requirements.txt
```

### Frontend Dependencies

No new dependencies required. Uses existing:
- `axios` - HTTP client
- `react-router-dom` - Routing
- `sonner` - Toast notifications

---

## How to Test End-to-End

### 1. Start the Backend

```bash
cd backend
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Expected startup log:
```
INFO: Auth config validated: Token expiry = 60 minutes
INFO: Authentication configuration validated
INFO: Application started successfully
```

### 2. Start the Frontend

```bash
cd frontend
npm start
```

### 3. Test the Authentication Flow

#### Registration Flow:

1. Navigate to `http://localhost:3000`
2. You'll be redirected to `/login`
3. Click the "Register" tab
4. Fill in the registration form:
   - Email: `test@example.com`
   - Password: `Test1234` (meets requirements)
   - Confirm Password: `Test1234`
   - Username: `testuser` (optional)
5. Click "Create Account"
6. You should see: ✅ "Registration successful! Please login."

#### Login Flow:

1. Switch to the "Login" tab
2. Enter credentials:
   - Email: `test@example.com`
   - Password: `Test1234`
3. Click "Login"
4. You should:
   - See: ✅ "Login successful!"
   - Be redirected to `/send`
   - See your user menu in the sidebar

#### Verify Protection:

1. While logged in, open DevTools → Application → Local Storage
2. Find `access_token` - this is your JWT
3. Navigate around the app (Send, Analyze, Chat, Analytics)
4. All pages should load successfully
5. Try to import Excel, send messages - everything should work

#### Test Logout:

1. Click on your user menu in the sidebar (bottom)
2. Click "Logout"
3. You should:
   - See: ℹ️ "Logged out successfully"
   - Be redirected to `/login`
   - No longer have `access_token` in localStorage
4. Try to manually navigate to `/send`
5. You should be redirected back to `/login`

---

## API Testing with cURL

### Register a User:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "api@example.com",
    "password": "ApiTest1234",
    "confirm_password": "ApiTest1234",
    "username": "apiuser"
  }'
```

Expected response:
```json
{
  "id": "uuid-here",
  "email": "api@example.com",
  "username": "apiuser",
  "roles": ["user"],
  "is_active": true,
  "created_at": "2025-11-18T..."
}
```

### Login:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "api@example.com",
    "password": "ApiTest1234"
  }'
```

Expected response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Access Protected Endpoint:

```bash
TOKEN="your-token-from-login"

curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

Expected response:
```json
{
  "id": "uuid-here",
  "email": "api@example.com",
  "username": "apiuser",
  "roles": ["user"],
  "is_active": true,
  "created_at": "2025-11-18T..."
}
```

### Try Protected Endpoint Without Token:

```bash
curl http://localhost:8000/api/analytics
```

Expected response (401 Unauthorized):
```json
{
  "detail": "Not authenticated"
}
```

---

## Database Inspection

Check MongoDB for created users:

```bash
# Connect to MongoDB
mongosh

# Use the database
use inboxhub_crm

# Find users
db.users.find().pretty()
```

You should see:
- `email` field
- `password_hash` field (hashed, not plain text!)
- `roles` array
- `created_at` timestamp

---

## Troubleshooting

### Issue: "AUTH_SECRET_KEY environment variable must be set"

**Solution:** Add `AUTH_SECRET_KEY` to your `.env` file

### Issue: "Could not validate credentials"

**Causes:**
1. Token expired (default 60 minutes)
2. Wrong token
3. `AUTH_SECRET_KEY` changed after token was generated

**Solution:** Logout and login again

### Issue: Frontend stuck on loading screen

**Cause:** Token in localStorage but user doesn't exist in database

**Solution:**
```javascript
// In browser console:
localStorage.removeItem('access_token')
location.reload()
```

### Issue: Password validation errors

**Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

**Valid examples:**
- `Test1234`
- `SecurePass99`
- `MyPassword1`

---

## Security Notes

### Production Checklist:

- [ ] Generate a strong random `AUTH_SECRET_KEY` (32+ characters)
- [ ] Never commit `.env` file to git
- [ ] Use HTTPS in production
- [ ] Consider migrating from localStorage to HttpOnly cookies
- [ ] Set appropriate `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES`
- [ ] Implement refresh tokens for better UX
- [ ] Add rate limiting on auth endpoints
- [ ] Monitor failed login attempts
- [ ] Implement password reset flow

### Token Storage:

**Current:** localStorage (acceptable for development)

**Recommended for Production:** HttpOnly cookies

localStorage pros:
- Simple to implement ✅
- Works with mobile apps ✅

localStorage cons:
- Vulnerable to XSS attacks ⚠️
- Visible in DevTools ⚠️

HttpOnly cookies pros:
- Not accessible via JavaScript (XSS protection) ✅
- Automatically sent with requests ✅

---

## File Structure

```
backend/
  auth/
    __init__.py          # Module exports
    models.py            # User models & validation
    security.py          # Password hashing & JWT utils
    dependencies.py      # FastAPI dependencies
    router.py            # Auth endpoints

  server.py              # Updated with auth integration
  .env.example           # Example environment variables

frontend/
  src/
    contexts/
      AuthContext.js     # Global auth state
    components/
      ProtectedRoute.js  # Route protection wrapper
      UserMenu.js        # User profile menu
    pages/
      LoginPage.js       # Login/Register UI
```

---

## Next Steps

1. ✅ Test the complete auth flow
2. ✅ Verify all protected routes require authentication
3. 🔄 Optionally add role-based permissions (admin vs user)
4. 🔄 Implement password reset functionality
5. 🔄 Add email verification
6. 🔄 Migrate to HttpOnly cookies for production

---

## Support

For issues or questions:
1. Check logs in `backend/app.log`
2. Check browser console for frontend errors
3. Verify environment variables are set correctly
4. Review `ARCHITECTURE_TODOS.md` for known issues
