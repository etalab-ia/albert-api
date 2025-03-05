Dans le dossier `helm`, un helmchart est disponible pour déployer albert-api et ses composants sur Kubernetes.

## Déploiement

- Créer un cluster kubernetes avec le fournisseur de votre choix
- Nous recommandons d'avoir au moins 3 noeuds, dont un avec un GPU dimensionné pour le LLM que vous souhaitez utiliser.
- Vérifier que la connexion avec votre cluster est fonctionnelle et que les noeuds sont disponibles avec `kubectl get nodes`
- Dans `helm/albert-stack/values.yaml`, remplacez les secrets et clé d'API par les valeurs de votre choix. 
  Vous pouvez aussi customiser votre déploiement via ce fichier, par exemple le tag de la version de l'API à déployer, le rate limiting, les clé d'API aux différents services déployés (redis, elastic search, Qdrant, etc), les ports, la configuration hardware demandée par chaque pod, etc.
- Depuis le dossier `helm`, installer le helm chart avec la commande `helm install albert-stack .`
- Surveillez le déploiement via le dashboard kubernetes, ou via un outil comme `k9s`.
- Si certains composants ne se lancent pas, ou sont bloqués en "Pending", vérifiez pourquoi avec `kubectl describe <pod_name>`.
- Si ils se lancent mais restent en erreur, vous pouvez vérifiez les logs avec `kubectl logs <pod_name>`
- La totalité de la stack peut prendre 15-20 minutes à se déployer
- Le déploiement "albert-api" va fail en boucle tant que les 2 déploiements "embedding" et "vllm" ne sont pas en "Running". 
- Une fois tous les services en "Running", vous pouvez obtenir l'IP publique du load balancer avec `kubectl describe svc albert-api`.
- Utiliser la valeur de `LoadBalancer Ingress` pour contacter l'API, par exemple :
```
curl http://YOUR_LOAD_BALANCER_INGRESS_IP/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GRIST_API_KEY" \
  -d '{
    "model": "meta-llama/Meta-Llama-3-8B-Instruct",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant."
      },
      {
        "role": "user",
        "content": "Qui es tu ?"
      }
    ]}'
```