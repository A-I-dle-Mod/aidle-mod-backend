# Summary

## Implemented Patreon account linking for logged-in users.

1. Database schema updates (prisma/schema.prisma)
   Added Patreon fields to the User model:
   **patreon_id**: Unique Patreon user ID
   **patreon_access_token**: OAuth access token
   **patreon_refresh_token**: OAuth refresh token
   **patreon_connected_at**: Timestamp when linked
   **is_patreon_subscriber**: Subscription status

2. Patreon OAuth routes (app/routes/patreon.py)
   **GET /patreon/oauth**: Returns Patreon OAuth URL for frontend redirect
   **GET /patreon/callback**: Handles Patreon OAuth callback, redirects to frontend
   **POST /patreon/link**: Links Patreon account to the logged-in user (uses JWT)
   **DELETE /patreon/unlink**: Unlinks Patreon account
   **GET /patreon/status**: Checks subscription status and refreshes tokens if needed

3. Features
   OAuth 2.0 flow integration
   Automatic token refresh
   Subscription verification (checks if user is an active patron)
   Account linking/unlinking
   Status checking with automatic token refresh

4. Router registration (app/main.py)
   Registered the Patreon router
   Next steps
   Run Prisma migration:
   > npx prisma migrate dev --name add_patreon_fields # or npx prisma db push

Set environment variables in your .env:

> PATREON_CLIENT_ID=your_patreon_client_id PATREON_CLIENT_SECRET=your_patreon_client_secret PATREON_REDIRECT_URI=http://localhost:8000/patreon/callback

Register your app with Patreon:

- Go to https://www.patreon.com/portal/registration/register-clients
- Create an OAuth client and get your client ID and secret
- Set the redirect URI to match your PATREON_REDIRECT_URI

The /me endpoint now includes Patreon fields. Users can link their Patreon account and access premium features based on their subscription status via is_patreon_subscriber.
