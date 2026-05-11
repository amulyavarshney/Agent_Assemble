import os
from typing import Any
from urllib.parse import quote

import httpx

from po_fastmcp.fhir_context import FhirContext

FhirResource = dict[str, Any]


# httpx defaults to 5s on every phase, which is too tight for real FHIR servers
# returning large Bundles. Make the read budget generous, keep connect tight so
# we fail fast on a wrong/down host. Override per-deployment via FHIR_HTTP_TIMEOUT.
_DEFAULT_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=float(os.getenv("FHIR_HTTP_TIMEOUT", "30")),
    write=30.0,
    pool=10.0,
)


class FhirClient:
    def __init__(self, context: FhirContext) -> None:
        self.context = context

    def _headers(self, *, include_content_type: bool = False) -> dict[str, str]:
        headers = {"Accept": "application/fhir+json"}
        if include_content_type:
            headers["Content-Type"] = "application/fhir+json"
            headers["Prefer"] = "return=representation"
        if self.context.token:
            token = self.context.token
            headers["Authorization"] = token if token.startswith("Bearer ") else f"Bearer {token}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)

    async def read(self, resource_type: str, resource_id: str) -> FhirResource | None:
        url = (
            f"{self.context.url}/"
            f"{quote(resource_type, safe='')}/"
            f"{quote(resource_id, safe='')}"
        )
        headers = self._headers()

        async with self._client() as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    async def put(
        self,
        resource_type: str,
        resource_id: str,
        resource: FhirResource,
    ) -> FhirResource:
        url = (
            f"{self.context.url}/"
            f"{quote(resource_type, safe='')}/"
            f"{quote(resource_id, safe='')}"
        )
        headers = self._headers(include_content_type=True)

        async with self._client() as client:
            response = await client.put(url, headers=headers, json=resource)

        response.raise_for_status()
        return response.json() if response.content else resource

    async def search(
        self,
        resource_type: str,
        search_parameters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[FhirResource]:
        url = f"{self.context.url}/{quote(resource_type, safe='')}"
        headers = self._headers()

        params = search_parameters or {}
        if limit:
            params["_count"] = limit

        async with self._client() as client:
            response = await client.get(url, headers=headers, params=params)

        response.raise_for_status()
        bundle = response.json()
        return [
            entry["resource"]
            for entry in bundle.get("entry", [])
            if "resource" in entry
        ]
