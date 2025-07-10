
import asyncio
import logging
import time
from typing import List, Optional, Tuple
from fastapi import UploadFile

from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers.models.routers._modelrouter import ModelRouter
from app.helpers._websearchmanager import WebSearchManager
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

logger = logging.getLogger(__name__)

# Prompts pour le deepsearch
class DeepSearchPrompts:
    @staticmethod
    def researcher(num_queries: int, lang: str = 'fr') -> str:
        if lang == 'en':
            return f"""You are an expert research assistant. Based on the user's request, generate up to {num_queries} distinct and simple search queries that would help gather information on the requested topic. Include keywords from the user's question in your search queries. If the user does not specify their country, assume they are from France and their request is in French. Respond only with a Python list, for example: ["query1", "query2"] and nothing else. The queries should not be similar."""
        return f"""Tu es un assistant expert en recherche. En te basant sur la demande utilisateur, génère jusqu'à {num_queries} distinctes
        différentes et simples requêtes de recherche (comme un humain le ferait) qui aideraient à recueillir des informations sur le sujet demandé. Dans tes requêtes mets aussi les mots clés présents dans la question de l'utilisateur.
        Si l'utilisateur ne précise pas son pays, part du principe qu'il est Français et que sa demande concerne la France.
        Réponds uniquement avec une liste python, par exemple : ["query1", "query2"] et ne dis rien d'autre. Les requêtes ne doivent pas se ressembler."""
    
    @staticmethod
    def evaluator(lang: str = 'fr') -> str:
        if lang == 'en':
            return """You are a critical research evaluator. Given the user's query and the content of a web page, determine if the web page contains useful information to answer the query. You only see an excerpt of the page. Respond with exactly one word: 'yes' if the page is useful or relevant to the query, or 'no' if it is not or does not seem useful. Do not include any additional text."""
        return """Vous êtes un évaluateur critique de recherche. Étant donné la requête de l'utilisateur et le contenu d'une page web,
        déterminez si la page web contient des informations utiles pour répondre à la requête. Vous ne voyez ici qu'un extrait de la page.
        Répondez avec exactement un mot : 'oui' si la page est utile ou en lien avec la requête, ou 'non' si elle ne l'est pas ou n'a pas l'air utile. N'incluez aucun texte supplémentaire"""

    @staticmethod
    def extractor(lang: str = 'fr') -> str:
        if lang == 'en':
            return """You are an expert in information extraction. Based on the user's request that led to this page and its content, extract and summarize all the information that could help answer the user's request. Respond only with the summary of the relevant context without additional comments. Keep only what is related to the user's query. Also provide the titles of the articles and the complete URLs in your response, starting the response with 'According to [title or url].' when possible. Eliminate all articles that do not discuss interesting things for the user's question. If nothing is interesting for the user, respond <next>."""
        return """Tu es un expert en extraction d'information, en te basant sur la demande utilisateur qui a amené à cette page, et son contenu, extrait et résume toutes les informations qui pourraient aider à répondre à la demande utilisateur.
        Réponds uniquement avec le résumé du contexte pertinent sans commentaire supplémentaire. Ne gardes que ce qui est en lien avec la requête utilisateur. Donnes aussi le titre des articles et les URLs complètes dans ta réponse en commençant la réponse par 'Selon [titre ou url].' quand c'est possible. 
        Elimine tous les articles qui ne parlent pas de choses intéressantes pour la question de l'utilisateur. Si rien n'est intéressant pour l'utilisateur, réponds <suivant>."""

    @staticmethod
    def analytics(lang: str = 'fr') -> str:
        if lang == 'en':
            return """You are an analytical research assistant. Based on the initial query, the searches conducted so far, and the contexts extracted from web pages, determine if further research is necessary to fully answer the user's query. If the context allows answering the user, respond []. Do not conduct unnecessary research. If the extracted contexts are empty or if further research is absolutely necessary, provide up to two new search queries in the form of a Python list (e.g., ["new query1", "new query2"]). If no further research is needed, respond only with an empty list []. Display only a Python list or [] without any additional text."""
        return """Vous êtes un assistant de recherche analytique. Sur la base de la requête initiale, des recherches effectuées jusqu'à présent et des contextes extraits des pages web, déterminez si des recherches supplémentaires sont nécessaires. 
        Si le contexte permet de répondre à l'utilisateur, répondez []. Ne fais pas de recherches inutiles.
        Si les contextes extraits sont vides ou si des recherches supplémentaires sont absolument nécessaires, fournissez jusqu'à deux nouvelles requêtes de recherche sous forme de liste Python (par exemple, ["new query1", "new query2"]). Si aucune recherche supplémentaire n'est nécessaire répondez uniquement avec une liste vide []. N'affichez qu'une liste Python ou une liste vide[] sans aucun texte supplémentaire.
        Ne fais jamais de recherches supplémentaires si le contexte est suffisant pour répondre à la question.
        """

    @staticmethod
    def redactor(lang: str = 'fr') -> str:
        if lang == 'en':
            return """You are an expert in drafting user request responses. Be polite. Based on the contexts gathered above and the initial query, write a complete, well-structured, and detailed response in markdown that answers the question thoroughly. Do not make an introduction, start directly with the answer. Include references in the form '[reference number]' in the paragraphs you write that refer to the references used. Include all useful information and conclusions without additional comments, as well as the names of articles and URLs present in the context that seem relevant. In the references, make sure not to duplicate and not to have more than 5, prioritizing URLs and titles. Start with the direct answer. Then detail."""
        return """Vous êtes un expert en rédaction de réponses de demande utilisateur. Soyez poli.
        Sur la base des contextes rassemblés ci-dessus et de la requête initiale, rédigez une réponse complète, 
        bien structurée en markdown et détaillée qui répond à la question de manière approfondie. Ne faites pas d'introduction, commencez tout de suite avec la réponse. Incluez des références sous la forme '[numero reference]' dans les paragraphes que vous rédigez qui renvoient aux références utilisées.
        Incluez toutes les informations et conclusions utiles sans commentaires supplémentaires, ainsi que les noms d'articles et urls présents dans le contexte qui semblent pertinents. Dans les références veillez à ne pas faire de doublons et à ne pas en avoir plus de 5 et priorisez les URLs et les titres. Commencez avec la réponse sans titre ou introduction. Détaillez ensuite.
        """


class TokenCounter:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    async def update_tokens(self, input_tokens: int, output_tokens: int):
        async with self.lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

    async def get_totals(self) -> Tuple[int, int]:
        async with self.lock:
            return self.total_input_tokens, self.total_output_tokens


class DeepSearchAgent:
    """Agent dédié au DeepSearch utilisant WebSearchManager."""

    def __init__(self, model: ModelRouter, web_search_manager: WebSearchManager):
        """Initialise l'agent DeepSearch avec WebSearchManager."""
        self.model = model
        self.web_search_manager = web_search_manager

    async def deep_search(
        self,
        prompt: str,
        session: AsyncSession,
        k: int = 5,
        iteration_limit: int = 2,
        num_queries: int = 2,
        lang: str = 'fr'
    ) -> Tuple[str, List[str], dict]:
        """
        Effectue une recherche approfondie avec WebSearchManager et itérations multiples.
        Retourne: (réponse_finale, sources, métadonnées)
        """
        start_time = time.time()
        aggregated_contexts = []
        aggregated_sources = []
        all_search_queries = []
        iteration = 0
        token_counter = TokenCounter()

        try:
            logger.info(f"Démarrage de la recherche approfondie pour : {prompt}")
            
            # Générer les requêtes de recherche initiales
            new_search_queries = await self._generate_search_queries(
                token_counter, prompt, num_queries, lang
            )
            
            if not new_search_queries:
                logger.warning("Aucune requête de recherche générée. Utilisation de la requête originale.")
                new_search_queries = [prompt]
                
            all_search_queries.extend(new_search_queries)
            logger.info(f"Requêtes de recherche initiales : {new_search_queries}")

            while iteration < iteration_limit:
                logger.info(f"=== Itération {iteration + 1} ===")
                iteration_contexts = []
                
                # Effectuer les recherches web via WebSearchManager
                for search_query in new_search_queries[:num_queries]:
                    logger.info(f"Recherche pour : {search_query}")
                    
                    # Obtenir la requête optimisée via WebSearchManager
                    web_query = await self.web_search_manager.get_web_query(search_query)
                    logger.info(f"Requête web optimisée : {web_query}")
                    
                    # Obtenir les résultats via WebSearchManager
                    results = await self.web_search_manager.get_results(web_query, k)
                    logger.info(f"Trouvé {len(results)} résultats pour '{web_query}'")
                    
                    # Traiter chaque résultat
                    for upload_file in results:
                        url = upload_file.filename.replace('.html', '') if upload_file.filename else 'unknown'
                        aggregated_sources.append(url)
                        
                        # Lire le contenu du fichier
                        content = await upload_file.read()
                        if isinstance(content, bytes):
                            content = content.decode('utf-8', errors='ignore')
                        
                        # Remettre le pointeur au début pour une éventuelle réutilisation
                        await upload_file.seek(0)
                        
                        # Traiter le contenu
                        context = await self._process_content(
                            token_counter, url, prompt, search_query, content, lang
                        )
                        if context:
                            iteration_contexts.append(context)

                if iteration_contexts:
                    aggregated_contexts.extend(iteration_contexts)
                    logger.info(f"Trouvé {len(iteration_contexts)} contextes utiles dans l'itération {iteration + 1}.")
                else:
                    logger.info(f"Aucun contexte utile trouvé dans l'itération {iteration + 1}.")

                # Vérifier si nous avons besoin d'autres itérations
                if iteration_limit > 1:
                    new_search_queries = await self._get_new_search_queries(
                        token_counter, prompt, all_search_queries, aggregated_contexts, lang
                    )
                else:
                    new_search_queries = []

                if new_search_queries == "[]":
                    logger.info("Le LLM indique qu'aucune recherche supplémentaire n'est nécessaire.")
                    break
                elif new_search_queries:
                    logger.info(f"Nouvelles requêtes de recherche pour l'itération {iteration + 2} : {new_search_queries}")
                    all_search_queries.extend(new_search_queries)
                else:
                    logger.info("Aucune nouvelle requête de recherche fournie. Fin de la recherche.")
                    break

                iteration += 1

            # Générer le rapport final
            logger.info("Génération du rapport final...")
            final_report = await self._generate_final_report(
                token_counter, prompt, aggregated_contexts, lang
            )
            
            total_input_tokens, total_output_tokens = await token_counter.get_totals()
            elapsed_time = time.time() - start_time
            
            metadata = {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "elapsed_time": elapsed_time,
                "iterations": iteration + 1,
                "total_queries": len(all_search_queries),
                "sources_found": len(aggregated_sources)
            }

            logger.info(f"Recherche terminée en {elapsed_time:.2f} secondes.")
            return final_report, aggregated_sources, metadata
                
        except Exception as e:
            logger.exception(f"Erreur lors de la recherche approfondie : {e}")
            raise

    # --- Méthodes de traitement ---

    async def _generate_search_queries(
        self, token_counter: TokenCounter, user_query: str, num_queries: int = 2, lang: str = 'fr'
    ) -> List[str]:
        prompt = DeepSearchPrompts.researcher(num_queries, lang)
        messages = [
            {"role": "system", "content": "You are a precise and helpful search assistant." if lang == 'en' else "Vous êtes un assistant de recherche précis et utile."},
            {"role": "user", "content": f"Demande utilisateur: {user_query}\n\n{prompt}"}
        ]
        response = await self._call_model_async(token_counter, messages, max_tokens=150)
        
        if response:
            try:
                search_queries = eval(response)
                if isinstance(search_queries, list):
                    return search_queries
                else:
                    logger.warning(f"Le LLM n'a pas retourné une liste. Réponse : {response}")
                    return []
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse des requêtes de recherche : {e}\nRéponse : {response}")
                return []
        return []

    def _clean_html_content(self, html_content: str) -> str:
        """Nettoie le contenu HTML pour le rendre lisible."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Supprimer les éléments non-content
            for element in soup(['script', 'style', 'meta', 'link', 'noscript', 'header', 'footer', 'aside']):
                element.decompose()
            
            text = soup.get_text(separator='\n')
            # Nettoyer les espaces
            cleaned_text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
            return cleaned_text
        except ImportError:
            logger.warning("BeautifulSoup non disponible, utilisation du contenu brut")
            return html_content
        except Exception as e:
            logger.warning(f"Erreur lors du nettoyage HTML : {e}")
            return html_content

    async def _is_content_useful(
        self, token_counter: TokenCounter, user_query: str, content: str, lang: str = 'fr'
    ) -> bool:
        if not content:
            return False
            
        prompt = DeepSearchPrompts.evaluator(lang)
        messages = [
            {"role": "system", "content": "You are a strict and precise evaluator of research relevance." if lang == 'en' else "Vous êtes un évaluateur strict et précis de la pertinence des recherches."},
            {"role": "user", "content": f"Requête utilisateur: {user_query}\n\nExtrait de page web (premiers 5000 caractères) :\n{content[:5000]}[...]\n\n{prompt}"}
        ]
        response = await self._call_model_async(token_counter, messages, max_tokens=10)
        if response:
            answer = response.strip().lower()
            return "oui" in answer or "yes" in answer
        return False

    async def _extract_relevant_context(
        self, token_counter: TokenCounter, user_query: str, search_query: str, 
        content: str, max_tokens: int = 1024, lang: str = 'fr'
    ) -> str:
        if not content:
            return ""
            
        prompt = DeepSearchPrompts.extractor(lang)
        messages = [
            {"role": "system", "content": "You are an expert in information extraction and synthesis." if lang == 'en' else "Vous êtes un expert dans l'extraction et la synthèse d'informations."},
            {"role": "user", "content": f"Requête utilisateur: {user_query}\nRequête de recherche: {search_query}\n\nContexte trouvé (premiers 20000 caractères) :\n{content[:20000]}\n\n{prompt}"}
        ]
        response = await self._call_model_async(token_counter, messages, max_tokens=max_tokens)
        if response:
            return response.strip()
        return ""

    async def _process_content(
        self, token_counter: TokenCounter, url: str, user_query: str, 
        search_query: str, content: str, lang: str = 'fr'
    ) -> str:
        logger.info(f"Traitement du contenu de : {url}")
        
        # Nettoyer le contenu HTML
        cleaned_content = self._clean_html_content(content)
        
        if not cleaned_content:
            logger.warning(f"Aucun contenu exploitable pour : {url}")
            return ''
        
        # Évaluer l'utilité
        is_useful = await self._is_content_useful(token_counter, user_query, cleaned_content, lang)
        logger.info(f"Utilité du contenu pour {url} : {is_useful}")
        
        if is_useful:
            context = await self._extract_relevant_context(
                token_counter, user_query, search_query, cleaned_content, lang=lang
            )
            if context and context.lower() not in ["<next>", "<suivant>"]:
                logger.info(f"Contexte extrait de {url} (premiers 200 caractères) : {context[:200]}")
                return f"[{url}] {context}"
        
        return ''

    async def _get_new_search_queries(
        self, token_counter: TokenCounter, user_query: str, previous_search_queries: List[str], 
        all_contexts: List[str], lang: str = 'fr'
    ):
        if not all_contexts:
            return await self._generate_search_queries(token_counter, user_query, 2, lang)
            
        context_combined = "\n".join([f"{context[:1000]} [...]" for context in all_contexts])
        prompt = DeepSearchPrompts.analytics(lang)
        messages = [
            {"role": "system", "content": "You are a systematic research planner." if lang == 'en' else "Vous êtes un planificateur de recherche systématique."},
            {"role": "user", "content": f"Contexte pertinent trouvé:\n{context_combined}\n\n{prompt}\nDemande utilisateur: {user_query}\nRecherches précédentes déjà effectuées: {previous_search_queries}"}
        ]
        response = await self._call_model_async(token_counter, messages, max_tokens=100)
        if response:
            cleaned = response.strip()
            logger.info(f"Réponse Analytics : {cleaned}")
            if "[]" in cleaned:
                logger.info("Recherche terminée")
                return "[]"
            try:
                new_queries = eval(cleaned)
                if isinstance(new_queries, list):
                    return new_queries
                else:
                    logger.warning(f"Le LLM n'a pas retourné une liste pour les nouvelles requêtes de recherche. Réponse : {response}")
                    return []
            except Exception as e:
                logger.error(f"Erreur lors de l'analyse des nouvelles requêtes de recherche : {e}\nRéponse : {response}")
                return []
        return []

    async def _generate_final_report(
        self, token_counter: TokenCounter, user_query: str, all_contexts: List[str], lang: str = 'fr'
    ) -> str:
        if not all_contexts:
            return "Aucune information pertinente trouvée pour répondre à votre requête."
            
        context_combined = "\n".join(all_contexts)
        prompt = DeepSearchPrompts.redactor(lang)
        messages = [
            {"role": "system", "content": "You are a talented assistant." if lang == 'en' else "Vous êtes un assistant talentueux."},
            {"role": "user", "content": f"Demande utilisateur: {user_query}\n\nContextes pertinents rassemblés:\n{context_combined}\n\n{prompt}\nRappel:\nDemande utilisateur: {user_query}"}
        ]
        report = await self._call_model_async(token_counter, messages, max_tokens=2048)
        return report or "Échec de génération d'un rapport."

    async def _call_model_async(
        self, token_counter: TokenCounter, messages: List[dict], max_tokens: int = 2048
    ) -> Optional[str]:
        await asyncio.sleep(0.1)  # Limitation du taux
        try:
            client = self.model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
            resp = await client.forward_request(
                method="POST",
                json={
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                    "model": self.model,
                },
            )
            if resp.status_code == 200:
                result = resp.json()
                try:
                    answer = result['choices'][0]['message']['content']
                    input_tokens = result.get('usage', {}).get('prompt_tokens', 0)
                    output_tokens = result.get('usage', {}).get('completion_tokens', 0)
                    await token_counter.update_tokens(input_tokens, output_tokens)
                    return answer
                except (KeyError, IndexError):
                    logger.error(f"Structure de réponse modèle inattendue : {result}")
                    return None
            else:
                logger.error(f"Erreur API modèle : {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Erreur lors de l'appel du modèle : {e}")
            return None