# Budget

## How it works

### User budget

Each user has a budget defined by POST `/v1/users` endpoint. The budget is defined in the `budget` field.

```bash
curl -X POST http://localhost:8000/v1/users \
-H "Authorization: Bearer <token>" \
-H "Content-Type: application/json" \
-d '{
    "name": "John Doe",
    "role": 1,
    "expires_at": "2025-01-01",
    "budget": 100
}'
```

Or by PATCH `/v1/users/{user_id}` endpoint to update the budget of an existing user.

```bash
curl -X PATCH http://localhost:8000/v1/users/1 \
-H "Authorization: Bearer <token>" \
-H "Content-Type: application/json" \
-d '{
    "budget": 100
}'
```

> **❗️Note**
> If budget is not defined, the user has no limit on the number of requests.

### Model costs

For each client model, is defined a costs in the `config.yml` file for the prompt and completion tokens (per million tokens). Example:

```yaml
models:
  - id: language-model
    type: text-generation
    clients:
      - model: openai/gpt-4o-mini
        type: openai
        costs:
          prompt_tokens: 0.1
          completion_tokens: 0.3
```

The compute cost is calculated based on the number of tokens used and the budget defined for the model based on the following formula:

```python
cost = round((prompt_tokens / 1000000 * client.costs.prompt_tokens) + (completion_tokens / 1000000 * client.costs.completion_tokens), ndigits=6)
```

The compute cost returned in the response, in the `usage.cost` field. After the request is processed, the budget amount of the user is updated by the `update_budget` function in the `hooks_decorator.py` file.
