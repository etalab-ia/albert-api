import urllib

import httpx


class HttpClient:
    def __init__(self, url):
        self.url = url

    async def get_datasets(self, query, limit):
        api_url_with_query = self._format_api_url_with_query(query, limit)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url_with_query)

            if response.status_code != 200:
                return {
                    "error": f"Erreur de l'API data.gouv.fr (HTTP {response.status_code})",
                    "details": response.text[:200] if response.text else "Pas de détails",
                }

            try:
                api_data = response.json()
            except Exception as e:
                return {"error": f"Réponse JSON invalide: {str(e)}"}

            return api_data
        except httpx.TimeoutException:
            return {"error": "Timeout lors de la requête vers data.gouv.fr"}
        except httpx.RequestError as e:
            return {"error": f"Erreur de requête: {str(e)}"}
        except Exception as e:
            return {"error": f"Erreur inattendue: {str(e)}"}

    def _format_api_url_with_query(self, query, limit):
        query_clean = query.strip().strip("?").strip()
        query_encoded = urllib.parse.quote(query_clean)
        api_url = f"{self.url}/datasets/?q={query_encoded}&page_size={limit}"
        return api_url
