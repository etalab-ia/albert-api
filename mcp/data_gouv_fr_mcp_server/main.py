#!/usr/bin/env python3
"""
Serveur MCP pour rechercher des jeux de données sur data.gouv.fr
"""

from typing import Dict, Any

from mcp.server.fastmcp import FastMCP

from infra.clients.http_client import HttpClient


class McpDataGouv:
    def __init__(self, http_client, name: str = "DataGouvFr"):
        self.mcp = FastMCP(name)
        self.http_client = http_client
        self._register_tools()

    def _register_tools(self):
        """Enregistre les outils MCP"""

        @self.mcp.tool()
        async def search_datasets(query: str, limit: int = 10) -> Dict[str, Any]:
            """
            Recherche des jeux de données sur data.gouv.fr

            Args:
                query: La requête de recherche (mots-clés)
                limit: Nombre maximum de résultats à retourner (défaut: 10)

            Returns:
                Dict contenant les résultats de la recherche
            """
            return await self._search_datasets_impl(query, limit)

    async def _search_datasets_impl(self, query: str, limit: int = 10) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"error": "La requête de recherche ne peut pas être vide"}

        api_data = await self.http_client.get_datasets(query, limit)

        datasets = api_data.get("data", [])

        resultats = self._to_mcp_tool_response(datasets)

        return {"query": query, "nombre_resultats": len(resultats), "total_disponible": api_data.get("total", 0), "resultats": resultats}

    def _to_mcp_tool_response(self, datasets):
        resultats = []
        for ds in datasets:
            dataset_id = ds.get("id", "")
            titre = ds.get("title", "Sans titre")
            description = ds.get("description", "")
            url = ds.get("page", "")  # 'page' est l'URL de la page du dataset

            organization = ds.get("organization", {})
            org_name = organization.get("name", "") if organization else ""

            tags = [tag for tag in ds.get("tags", [])]
            created_at = ds.get("created_at", "")
            last_modified = ds.get("last_modified", "")

            resources = ds.get("resources", [])
            formats = list(set([res.get("format", "").upper() for res in resources if res.get("format")]))

            dataset_info = {
                "id": dataset_id,
                "titre": titre,
                "description": description[:500] + ("..." if len(description) > 500 else ""),  # Limiter la description
                "url": url,
                "organisation": org_name,
                "tags": tags[:5],
                "formats_disponibles": formats,
                "date_creation": created_at.split("T")[0] if created_at else "",
                "derniere_modification": last_modified.split("T")[0] if last_modified else "",
                "nombre_ressources": len(resources),
            }

            resultats.append(dataset_info)
        return resultats


if __name__ == "__main__":
    http_client = HttpClient("https://www.data.gouv.fr/api/1")
    mcp_data_gouv = McpDataGouv(http_client, "DataGouvFr")

    mcp_data_gouv.mcp.run()
