# OAuth2 Configuration with Encryption

## Generating a Secure Encryption Key

To generate a secure encryption key for OAuth2, use the following command:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

This command generates a 32-byte key encoded in URL-safe base64, perfect for Fernet.

## Configuration

### In config.yml (backend API)

```yaml
oauth2:
  client_id: your_proconnect_client_id
  client_secret: your_proconnect_client_secret
  server_metadata_url: https://identite-sandbox.proconnect.gouv.fr/.well-known/openid-configuration
  redirect_uri: https://your-domain.gouv.fr/v1/oauth2/callback
  scope: "openid profile email"
  allowed_domains:
    - localhost  # For development
    - gouv.fr    # Allowed domains in production
  default_role: Freemium
  encryption_key: YOUR_GENERATED_KEY_HERE  # Key generated with the command above
```

### In config.yml (Streamlit UI)

```yaml
playground:
  api_url: http://localhost:8000
  oauth2_encryption_key: YOUR_GENERATED_KEY_HERE  # Same key as the backend
```

## Security

- **Important**: The encryption key must be the same between the backend and the user interface
- **Production**: Never use "changeme" in production
- **TTL**: Encrypted tokens have a lifespan of 5 minutes (300 seconds)
- **Rotation**: Regularly change the encryption key in production

## How It Works

1. **OAuth2 Login**: The user logs in via ProConnect
2. **Callback**: The backend receives OAuth2 tokens
3. **Encryption**: The tokens (app_token, token_id, proconnect_token) are encrypted together
4. **Redirection**: The user is redirected to the UI with the encrypted token
5. **Decryption**: The UI decrypts the token and extracts the information
6. **Session**: A user session is created with the tokens

## Error Handling

If decryption fails (expired token, incorrect key, etc.), the user sees an error message and is prompted to reconnect.

## ProConnect Token

The ProConnect token (id_token) is stored to enable ProConnect-side logout in the future. It is accessible via:

```python
proconnect_token = st.session_state.get("proconnect_token")
```
