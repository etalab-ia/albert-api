# Code architecture

```mermaid  
---
config:
  layout: elk
  elk:
    mergeEdges: true

---
flowchart LR
    config@{ shape: tag-doc, label: "config.yml" }
    
    subgraph **main.py**
    settings[utils/settings.py]
    lifespan[utils/lifespan.py]

    config --> settings
    settings --> lifespan
    end

    subgraph **app/clients**
    redisclient[Redis - ConnectionPool]
    sqlclient[SQLAlchemy - AsyncSession]
    qdrantclient[Qrant - AsyncQdrantClient]
    internetclient[BraveInternetClient<br>DuckduckgoInternetClient]
    modelclient@{ shape: processes, label: "VllmModelClient<br>TeiModelClient<br>AlbertModelClient<br>OpenaiModelClient" }
    
    lifespan --> redisclient
    lifespan --> sqlclient
    lifespan --> qdrantclient
    lifespan -- one of two--> internetclient
    lifespan -- for each model --> modelclient

    style redisclient stroke-dasharray: 5 5
    style qdrantclient stroke-dasharray: 5 5
    end
    
    subgraph **app/helpers**
    modelrouter@{ shape: processes, label: "ModelRouter" }
    modelregistry[ModelRegistry]
    identityaccessmanager[IdentityAccessManager]
    documentmanager[DocumentManager]
    limiter[Limiter]

    modelclient --> modelrouter
    modelrouter --> modelregistry
    sqlclient --> identityaccessmanager
 
    internetclient --> websearchmanager
    websearchmanager --> documentmanager
    sqlclient --> documentmanager
    qdrantclient --> documentmanager
    redisclient --> limiter

    style documentmanager fill:blue,stroke:#000,stroke-width:1px,color:#fff
    style modelregistry fill:orange,stroke:#000,stroke-width:1px,color:#fff
    style identityaccessmanager fill:purple,stroke:#000,stroke-width:1px,color:#fff
    style limiter fill:black,stroke:#000,stroke-width:1px,color:#fff
    end

    subgraph **app/endpoints**
    documentsendpoints[documents]
    searchendpoints[search]
    modelsendpoints[models]
    chatendpoints[chat]
    audioendpoints[audio]
    completionsendpoint[completions]
    embeddingsendpoints[embeddings]
    rerankendpoints[rerank]
    collectionsendpoints[collections]
    authendpoints[auth]

    modelregistry ==> modelsendpoints
    modelregistry ==> chatendpoints
    modelregistry ==> completionsendpoint
    modelregistry ==> embeddingsendpoints
    modelregistry ==> rerankendpoints
    modelregistry ==> searchendpoints
    modelregistry ==> documentsendpoints
 
    identityaccessmanager ==> authendpoints

    documentmanager ==> documentsendpoints
    documentmanager ==> searchendpoints
    documentmanager ==> collectionsendpoints


    end
    
    subgraph **depends.py**
    authorization[Authorization]

    limiter ====> authorization
    identityaccessmanager ===> authorization
    modelregistry ===> authorization

    style authorization fill:red,stroke:#000,stroke-width:1px,color:#fff
    end

    authorization ==all endpoints==> **app/endpoints**
```