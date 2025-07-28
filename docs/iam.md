# Identity and Access Management

## Overview

OpenGateLLM implements a security system based on users, roles, and permissions. This documentation explains how to manage security within the system, with special focus on the master key, user authentication, and role-based access control.

## Authentication System

The security model consists of three main components:
- Roles: Define sets of permissions and usage limits
- Users: Entities that can access the API with assigned roles
- Tokens: API keys that authenticate user requests

## Master Key

### What is the Master Key?

The master key is a special API key that:
- Is used for initial system setup
- Grants access to the API with unlimited permissions
- Encrypts all user tokens for security
- Cannot be modified or deleted through the API

### Configuration

The master key is defined in the auth section of the configuration file:

```yaml
auth:
  master_username: "master"
  master_key: "changeme"
```

> **❗️Note**<br>
> The default values `master_username` and `master_key` should be replaced with a strong, unique secret key in production environments.

[See configuration documentation for more information](./deployment.md#auth)

## Using the Master Key

The master key serves several critical purposes:
- Initial System Setup: When the database is empty, the master user can create the first roles and users
- Emergency Access: Provides a failsafe way to access the system if regular authentication fails
- Token Encryption: Used to encrypt all user tokens, ensuring they cannot be compromised

> **⚠️ Warning**<br>
> If you modify the master key, you'll need to update all user API keys since they're encrypted using this key.

## Role Management

Roles define what actions users can perform within the system through permissions, and what resource limits apply.

### Role Properties

- Name: unique identifier for the role
- Default: whether this is the default role assigned to new users (for Playground UI)
- Permissions: list of actions the role can perform
- Limits: resource usage limits for users with this role

> **❗️Note**<br>
> All permissions and limits are managed by the *[Authorization](../app/helpers/_authorization.py)* class.

### Available Permissions

| Permission               | Description |
| ------------------------ | ----------- |
| CREATE_ROLE              | Create a new role |
| READ_ROLE                | Read a role |
| UPDATE_ROLE              | Update a role |
| DELETE_ROLE              | Delete a role |
| CREATE_USER              | Create a new user and a token for other users |
| READ_USER                | Read a user |
| UPDATE_USER              | Update a user |
| DELETE_USER              | Delete a user |
| CREATE_PUBLIC_COLLECTION | Create a public collection |
| READ_METRIC              | Read prometheus `/metrics` endpoint |

### Limits

Limits define model usage limits for users with this role. A limit is a tuple of `model`, `type` and `value`.

Example: `("gpt-4o", "TPM", 1000)`

The `type` can be:
- `TPM`: tokens per minute
- `RPM`: requests per minute
- `TPC`: tokens per collection
- `RPC`: requests per collection

If value is `None`, the limit is not applied.

### Managing Roles

The API provides endpoints to:
- Create roles (POST `/v1/roles`)
- View roles (GET `/v1/roles`, GET `/v1/roles/{role_id}`)
- Update roles (PATCH `/v1/roles/{role_id}`)
- Delete roles (DELETE `/v1/roles/{role_id}`)

*Example role creation:*

```json
POST /v1/roles
{
  "name": "Admin",
  "default": false,
  "permissions": ["CREATE_USER", "READ_USER", "UPDATE_USER", "DELETE_USER"],
  "limits": [
    {
      "model": "my-language-model",
      "type": "tpm",
      "value": 100000
    }
  ]
}
```

## User Management

Users represent entities that can access the API.

### User Properties

- Name: Username for identification
- Role: The assigned role ID that determines permissions and limits
- Expires At: Optional timestamp when the user account expires

### Managing Users

The API provides endpoints to:
- Create users (POST `/v1/users`)
- View users (GET `/v1/users`, GET `/v1/users/{user_id}`)
- Update users (PATCH `/v1/users/{user_id}`)
- Delete users (DELETE `/v1/users/{user_id}`)

*Example user creation:*

```json
POST /v1/users
{
  "name": "john_doe",
  "role": 1,
  "expires_at": 1735689600  // Optional, Unix timestamp
}
```

## Token Management

Tokens are the API keys used to authenticate requests.

### Token Properties

- Name: Descriptive name for the token
- Expires At: Optional timestamp when the token expires

### Managing Tokens

The API provides endpoints to:

- Create tokens (POST `/v1/tokens`)
- View tokens (GET `/v1/tokens`, GET `/v1/tokens/{token_id}`)
- Delete tokens (DELETE `/v1/tokens/{token_id}`)

Example token creation:

```json
POST /v1/tokens
{
  "name": "Development API Key",
  "expires_at": 1704067200  // Optional, Unix timestamp
}
```

> **❗️Note**<br>
> `CREATE_USER` permission allows to create tokens for other users with `user` field in the request body of POST `/v1/tokens`. These tokens are not subject to the `max_token_expiration_days` limit set in the auth section of the configuration file.
