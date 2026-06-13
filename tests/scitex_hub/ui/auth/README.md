# E2E Auth Tests

## test_login.py
- Login page loads
- Login page has signup link
- Login page has forgot password link
- Login with valid credentials
- Login redirects to home
- Login with wrong password
- Login with nonexistent user
- Login with empty fields
- Logout clears session
- Logout redirects to public page
- Authenticated user stays logged in
- Accessing signin while logged in redirects

## test_signup.py
- Signup page loads
- Signup page has required fields
- Signup page has login link
- Signup rejects invalid email
- Signup rejects weak password
- Signup rejects mismatched passwords
- Signup rejects short username
- Signup rejects existing username
- Signup form clears on focus
- Username check API exists

## test_password_reset.py
- Reset page loads
- Reset page has email field
- Reset page has login link
- Reset with valid email submits
- Reset with invalid email shows error
- Reset with empty email shows error
