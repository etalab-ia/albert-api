# Routing

L'API Albert permet de configurer pour chaque modèle un ou plusieurs clients vers des API externes. Ces clients sont définis dans le fichier de configuration (voir [deployment](./deployment.md)). Un modèle peut avoir plusieurs clients.

## Exemple de configuration

Dans cet exemple, nous configurons le modèle `turbo` est lié à deux clients : un client OpenAI et un client vLLM. Le modèle peut être appelé avec l'ID `turbo` ou avec l'alias défini dans l'entrée `aliases` : `turbo-alias`.

La stratégie de routage est définit à `round_robin` ce qui signifie que les requêtes seront distribuées alternativement entre les deux clients. Pour plus d'information sur les stratégies de routage, voir [deployment](./deployment.md).

Chaque client va appelé un modèle différent, définit par l'entrée `model`. Par exemple, le client OpenAI va appelé le modèle `gpt-3.5-turbo` et le client vLLM va appelé le modèle `meta-llama/Llama-3.1-8B-Instruct`.

>❗️ Attention, lorsque vous définissez plusieurs clients pour un modèle, nous recommandons que ces clients soit du même type et appelle le même modèle. En effet, les réponses pourraient avoir des structures différentes dans le cas inverse.

```yaml 
models:
  - id: turbo
    type: text-generation
    aliases: ["turbo-alias"]
    routing_strategy: round_robin
    clients:
      - model: gpt-3.5-turbo 
        type: openai
        args:
          base_url: https://api.openai.com/v1
          api_key: sk-...sA
          timeout: 60
      - model: meta-llama/Llama-3.1-8B-Instruct
        type: vllm
        args:
          base_url: http://.../v1
          api_key: sf...Df
          timeout: 60
```

## Logique de code

Au démarrage de l'API un objet `ModelRegistry` est créé qui contient les objets `ModelRouter` pour chaque modèle définit dans l'entrée `models` du fichier de configuration. Ces derniers contiennent un objet `ModelClient` pour chaque client définit dans l'entrée `clients` du modèle dans le fichier de configuration.

### ModelRegistry

ModelRegistry est un classe utilisable comme un dictionnaire pour récupérer un modèle. Le modèle est récupéré par son ID ou un de ses alias définit dans le fichier de configuration (voir [deployment](./deployment.md)).

```python
from app.utils.lifespan import models

model = models["guillaumetell-7b"]
```

Si le modèle n'existe pas, l'API renverra une erreur HTTP 404 `Model not found`, plutôt qu'une `KeyError`. 

L'objet retourné est un objet `ModelRouter` qui contient les informations du modèle et les clients associés.

### ModelRouter

L'objet `ModelRouter` contient les informations du modèle et les clients associés. Cette classe contient une méthode `get_client` qui permet de récupérer un client du modèle. S'il existe plusieurs clients, la méthode va sélectionner un client en fonction de la stratégie de routage (`routing_strategy`) définit dans le fichier de configuration (voir [deployment](./deployment.md)).

Les informations du modèle sont celle renvoyées par le endpoint `GET /v1/models` :

- `id` : l'ID du modèle par lequel les utilisateurs peuvent identifier le modèle
- `type` : le type de modèle (voir [models](./models.md))
- `aliases` : les alias du modèle
- `max_context_length` : la longueur maximale d'input du modèle


```python
from app.utils.lifespan import models

model = models["guillaumetell-7b"]

client = model.get_client(endpoint="chat/completions")
```

Le paramètre `endpoint` est optionnel. Si ce paramètre n'est pas renseigné, la méthode `get_client` va vérifier que le type du modèle est compatible avec l'endpoint recherché.

### ModelClient

L'objet `ModelClient` est un objet de type `AsyncOpenAI` qui permet d'appeler l'API externe grâce à 3 attributs :
- `base_url` : l'URL de l'API externe
- `api_key` : la clé API de l'API externe
- `model` : le modèle ID de l'API externe

Il y existe plusieurs classes de ModelClient, par exemple `VllmModelClient` ou `OpenAIModelClient`. Chacun définit une variable `ENDPOINT_TABLE` qui contient les endpoints de l'API externe qui sont supportés par le client et permet de faire la correspondance entre l'endpoint de l'API externe et l'endpoint de l'API Albert.

## Stratégies de routage

### Shuffle

La stratégie `shuffle` distribue les requêtes entre les clients de manière équilibrée aléatoirement.

### Round robin

La stratégie `round_robin` distribue les requêtes entre les clients de manière alternative.
