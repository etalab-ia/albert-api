# Sécurité

## Authentification

L'authentification est réalisée par le biais d'un client [Grist](https://www.getgrist.com/). Vous devez créer une table dans Grist pou stocker les clefs d'API keys que vous créez. Cette table doit avoir la structure suivante 

| KEY | ROLE | EXPIRATION |
| --- | --- | --- |
| my_key | admin \| client \| user | 2099-01-01 |

Si vous souhaitez déployer l'API sans authentication par Grist, ne déclarez pas de section *auth* dans le fichier de configuration. L'authentification sera alors désactivée et l'utilisateur est le rôle de niveau 2 (admin).

## Droits d'accès

L'API implémente un système de rôle à 3 niveaux : 

| Niveau du rôle | Description |
| --- | --- |
| 0 (user) | Accès limité à l'API (rate limiting) et aucun droits d'édition sur les collections publiques |
| 1 (client) | Accès illimité à l'API et aucun droits d'édition sur les collections publiques |
| 2 (admin) | Accès illimité à l'API et droits d'édition sur toutes les collections |

Par défaut, le rate limiting est de 100 requêtes par minute pour tous les niveaux. Il est de 10 requêtes par minute pour le niveau 0 (user) pour les endpoints tagués *Core*.
