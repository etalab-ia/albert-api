# Albert API ProConnect

## Proconnect Integration

Add a ProConnect connection button on login page. The button is implemented as an HTML form that directly redirects to Albert API's OAuth2 endpoint.

Generate a Albert API key on ProConnect successful authentication callback as follows:

```mermaid
sequenceDiagram
    actor User
    participant StreamLit as Playground (Streamlit)
    participant FastAPI as Albert API (FastAPI)
    participant ProConnect as ProConnect
    participant Database as Database
    
    User->>StreamLit: Clicks on "ProConnect" button
    Note over StreamLit: HTML form redirects browser
    StreamLit->>FastAPI: GET /v1/oauth2/login<br>(with referer header from Streamlit)
    
    Note over FastAPI: SessionMiddleware handles cookies<br>for OAuth state management
    FastAPI->>FastAPI: Creates state with original_url + timestamp<br>(for security and expiration)
    FastAPI->>ProConnect: Redirect to authorization URL<br>(client_id, redirect_uri, response_type, scope, state)
    
    ProConnect->>User: Authentication request
    User->>ProConnect: Provides credentials
    ProConnect->>User: Consent request
    User->>ProConnect: Gives consent
   
    ProConnect->>FastAPI: Redirect to callback URL<br>GET /v1/oauth2/callback?code=...&state=...
    
    FastAPI->>FastAPI: Validates state parameter<br>(timestamp + original_url)
    FastAPI->>ProConnect: Exchange code for tokens<br>(authorize_access_token)
    ProConnect->>FastAPI: Returns access_token + id_token

    FastAPI->>ProConnect: Get user_info using access_token
    ProConnect->>FastAPI: Returns user info (sub, email, given_name, usual_name)

    FastAPI->>FastAPI: Extracts user information<br>(sub, email, given_name, usual_name)
    
    FastAPI->>Database: Searches for user by sub or email
    Database->>FastAPI: Returns user or null
    
    alt User not found
        FastAPI->>Database: Creates new user with default role
        Database->>FastAPI: Returns user_id
    else User found but email changed
        FastAPI->>Database: Updates user email
    end
    
    FastAPI->>Database: Refresh/create API token for user
    Database->>FastAPI: Returns app_token + token_id
    
    FastAPI->>FastAPI: Validates request origin against allowed_domains<br>Encrypts tokens (app_token, token_id, proconnect_token)
    FastAPI->>StreamLit: Redirect with encrypted data<br>(origin?encrypted_token=...)
    
    StreamLit->>StreamLit: Decrypts token with TTL validation<br>Extracts app_token, token_id, proconnect_token
    StreamLit->>StreamLit: Stores tokens in session_state<br>Sets login_status = True
    StreamLit->>User: Displays authenticated interface
```

## Key points 

### Implementation Details

* **Button Implementation**: Uses HTML form with direct POST to Albert API (not st.login component). This leverages browser navigation for OAuth flow.
* **Session Management**: FastAPI SessionMiddleware handles cookies and state management during OAuth flow (provides security against CSRF and manages temporary state).
* **Token Security**: Uses our own encrypted tokens instead of directly using ProConnect tokens. This provides better control and security.
* **Logout Implementation**: ✅ Implemented with `/v1/oauth2/logout` endpoint that handles both local token invalidation and ProConnect logout.

### User Information Processing

Reliable [USERINFO](https://partenaires.proconnect.gouv.fr/docs/ressources/glossaire) fields used:
```json
{
  "sub": "704e024229015d2bd47f7a5e5ab05b35c8336ab403c38022985f8cfadc86fe91",  // Primary identifier
  "email": "test@abcd.com",          // Secondary identifier 
  "given_name": "Angela Claire Louise", // User display name
  "usual_name": "DUBOIS"             // User surname
}
```

### Security & Configuration

* **Default Role Assignment**: Creates users with `configuration.dependencies.proconnect.default_role` (configurable in config.yml)
* **Domain Validation**: Strict validation against `allowed_domains` configuration prevents unauthorized redirects
* **Multi-Application Support**: ✅ Multiple applications can use the same Albert API OAuth callback (controlled by `allowed_domains`)
* **Token Encryption**: ✅ API keys are encrypted in redirect URLs using time-limited encryption (5-minute TTL) with shared secret
* **State Validation**: OAuth state includes timestamp validation (10-minute window) to prevent replay attacks