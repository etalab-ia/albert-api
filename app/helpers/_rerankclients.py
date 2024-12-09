import re

from app.helpers._modelclients import ModelClients


class RerankClient:
    PROMPT_LLM_BASED = """Voila un texte : {doc}\n 
        En se basant uniquement sur ce texte, réponds 1 si ce texte peut donner des éléments de réponse à la question suivante ou 0 si aucun élément de réponse n'est présent dans le texte. Voila la question: {prompt}
        Le texte n'a pas besoin de répondre parfaitement à la question, juste d'apporter des éléments de réponses et/ou de parler du même thème. Réponds uniquement 0 ou 1."""
    PROMPT_CHOICER = """
Tu es un expert en compréhension et en évaluation des besoins en information pour répondre à un message utilisateur. Ton travail est de juger la possibilité de répondre à un message utilisateur en fonction d'un contexte donné.
Nous sommes en 2024 et ton savoir s'arrete en 2023.

Le contexte est composé d'une liste d'extrait d'article qui sert d'aide pour répondre au message utilisateur, mais n'est pas forcément en lien avec lui. Tu dois évaluer s'il y a besoin du contexte ou non.

Ne réponds pas au message utilisateur.
Voilà le message utilisateur : {prompt}
 
Voilà tes choix :

- Si le message utilisateur n'est vraiment pas claire ou ne veut vraiment rien dire en français réponds 0 OU
- Si le message utilisateur est compréhensible et que le contexte donné est en lien avec le message utilisateur (même de loin, même un seul article du contexte) / Si le message utilisateur aborde un sujet qui est également abordé dans le contexte réponds 1 OU
- Si le contexte contient certains éléments qui peuvent aider à répondre au message utilisateur réponds 1 OU
- Si le message utilisateur demande explicitement des sources ou des références réponds 1 (si le contexte associé est bon) ou 3 (si le contexte associé est mauvais) OU
- Si le message utilisateur n'a pas besoin de contexte car ce n'est pas une question adminitrative / c'est de la culture générale simple réponds 2 OU
- Si le message utilisateur est un message simple ou personnel / Le reste de la conversation permets d'y répondre réponds 2 OU
- Si le message utilisateur a besoin de contexte car elle est spécifique, sur de l'administratif, ou complexe, mais qu'aucun des articles du contexte n'est en lien avec elle réponds 3
- Si on te demande de chercher sur internet / qu'on te demande des informations sur quelqu'un ou une personnalité / qu'on te demande des informations actuelles / si le message utilisateur commence par "internet" réponds 4

Pour chaque choix, assure-toi de bien évaluer le message utilisateur selon ces critères avant de donner ta réponse. 
Regardes bien le contexte, s'il peut t'aider à répondre au message utilisateur c'est important.
Même si le contexte ne contient que quelques informations ou mots commun avec le message utilisateur, considère qu'il est en lien avec la question.

Ne fais pas de phrase, réponds uniquement 0, 1, 2, 3 ou 4.

Exemples
----------
Exemple 1 - "Le contexte permet de répondre à la question"
context : Pour la retraite anticipée [...]
question : Comment bien préparer sa retraite ?
reponse : 1
Exemple 2 - "toto voiture n'est pas une question et ne veut rien dire"
context : les assurances de véhicules [...]
question : toto voiture
reponse : 0
Exemple 3 : "Pas besoin de contexte, la question est de la culture générale / facile"
context : En cas de vol ou de perte [...]
question : Quelle est la capitale de la France ?
reponse : 2
Exemple 4 : "Question necessitant du contexte pertinent mais pas dans le rag"
context : Vous pouvez faire une demarche [...]
question : Qui est le président des usa actuellement ?
reponse : 4
----------

Ne réponds pas à la question, réponds uniquement 0, 1, 2, 3 ou 4. Ne donnes jamais d'explication ou de phrase dans ta réponse, renvoies juste un chiffre. Ta réponse doit être sous ce format:<CHIFFRE>
Bases toi également sur le reste des messages de la conversation pour répondre avec ton choix.
context : {docs}
question : {prompt}
reponse :
    """

    def __init__(
        self,
        model_clients: ModelClients,
    ):
        self.model_clients = model_clients

    def get_rank(self, prompt: str, inputs: list, model: str, rerank_type: str) -> str:
        if rerank_type == "classic_rerank":
            # TODO: Add classic reranker
            return []

        elif rerank_type == "llm_rerank":
            prompts = []
            for doc in inputs:
                prompt_ = self.PROMPT_LLM_BASED.format(prompt=prompt, doc=doc)
                prompts.append(prompt_)

            results = []
            for prompt in prompts:
                response = self.model_clients[model].chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_clients[model],
                    temperature=0.1,
                    max_tokens=3,
                    stream=False,
                )
                result = response.choices[0].message.content

                match = re.search(r"[0-1]", result)
                result = int(match.group(0)) if match else 0
                results.append(result)
            return results
        # TODO: choicer
        elif rerank_type == "choicer":
            prompt = self.PROMPT_CHOICER.format(prompt=prompt, docs=inputs)

            print("###################")
            print(prompt)
            print("###################")

            response = self.model_clients[model].chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,  # self.model_clients[model],
                temperature=0.1,
                max_tokens=3,
                stream=False,
            )
            result = response.choices[0].message.content
            print("YEEEE", result)

            match = re.search(r"[0-4]", result)
            result = int(match.group(0)) if match else 0
            return result
