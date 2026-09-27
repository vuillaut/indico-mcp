"""Thin async wrapper around the Indico HTTP endpoints this server uses.

Three kinds of endpoints are involved:

- the documented export API (`/export/...json`) and `/api/...` endpoints;
- internal JSON REST endpoints under `/event/<id>/manage/...`;
- internal WTForms dialogs, which return HTML (see `forms.py`).

The last two are not a public API. They work with a personal token that has
the "Everything (all methods)" scope, and they may change between Indico
versions. They were checked against Indico 3.3.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import httpx
from bs4 import BeautifulSoup

from indico_mcp.forms import FormValue, ParsedForm, parse_form

USER_AGENT = "indico-mcp/0.1"


class IndicoError(Exception):
    """An Indico request failed; the message is meant for the agent."""


class IndicoClient:
    def __init__(self, http: httpx.AsyncClient, token: str | None):
        self.http = http
        self.token = token

    def _headers(self, xhr: bool) -> dict[str, str]:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/html;q=0.9"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if xhr:
            # makes Indico's dialogs answer with JSON instead of a full page
            headers["X-Requested-With"] = "XMLHttpRequest"
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any = None,
        data: list[tuple[str, str]] | None = None,
        files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
        xhr: bool = False,
    ) -> httpx.Response:
        form_data = _group(data) if data is not None else None
        response = await self.http.request(
            method,
            path,
            params={k: v for k, v in (params or {}).items() if v is not None},
            json=json_body,
            data=form_data,
            files=files,
            headers=self._headers(xhr),
        )
        if response.is_redirect:
            location = response.headers.get("location", "")
            if "login" in location:
                raise IndicoError(
                    f"{method} {path}: Indico redirected to the login page. The token is missing, "
                    "invalid, or lacks the scope this endpoint needs."
                )
            raise IndicoError(f"{method} {path}: unexpected redirect to {location}")
        if response.status_code >= 400:
            raise IndicoError(f"{method} {path}: {_describe_error(response)}")
        return response

    async def get_json(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        return _json(await self.request("GET", path, params=params))

    async def export(self, path: str, **params: Any) -> Any:
        """Call the classic export API: `/export/<path>.json`."""
        payload = await self.get_json(f"/export/{path}.json", params)
        return payload.get("results", payload) if isinstance(payload, dict) else payload

    async def rest(self, method: str, path: str, json_body: Any = None) -> Any:
        response = await self.request(method, path, json_body=json_body, xhr=True)
        return _json(response) if response.content else None

    async def get_form(self, path: str, params: Mapping[str, Any] | None = None) -> ParsedForm:
        response = await self.request("GET", path, params=params, xhr=True)
        form = parse_form(_html_of(response))
        if not form.known:
            raise IndicoError(f"GET {path}: no form found in the response (no access, or the page changed)")
        return form

    async def submit_form(
        self,
        path: str,
        fields: list[tuple[str, str]],
        *,
        params: Mapping[str, Any] | None = None,
        files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
    ) -> dict[str, Any]:
        response = await self.request("POST", path, params=params, data=fields, files=files, xhr=True)
        try:
            payload = response.json()
        except ValueError:
            payload = {"html": response.text}
        if isinstance(payload, dict) and payload.get("success"):
            return payload
        # Indico answers a failed validation with the re-rendered form
        errors = parse_form(payload.get("html", "") if isinstance(payload, dict) else "").errors
        if errors:
            details = "; ".join(f"{name}: {message}" for name, message in errors.items())
            raise IndicoError(f"POST {path}: Indico rejected the form: {details}")
        raise IndicoError(f"POST {path}: Indico did not accept the form (no success flag, no field errors)")

    async def edit_form(
        self,
        path: str,
        overrides: Mapping[str, FormValue],
        *,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load a form, change only `overrides`, and submit it."""
        form = await self.get_form(path, params)
        unknown = sorted(set(overrides) - form.known)
        if unknown:
            raise IndicoError(
                f"{path}: the form has no field(s) {unknown}; this Indico version may differ. "
                f"Available fields: {sorted(form.known)}"
            )
        return await self.submit_form(path, form.merged(overrides), params=params)


def _group(fields: list[tuple[str, str]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for name, value in fields:
        grouped.setdefault(name, []).append(value)
    return grouped


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise IndicoError(
            f"{response.request.method} {response.request.url.path}: expected JSON, got "
            f"{response.headers.get('content-type', 'unknown content')}"
        ) from exc


def _html_of(response: httpx.Response) -> str:
    if "json" not in response.headers.get("content-type", ""):
        return response.text
    payload = response.json()
    return payload.get("html", "") if isinstance(payload, dict) else ""


_STATUS_HINTS = {
    401: "authentication failed; check the Indico token",
    403: (
        "forbidden; the user may lack rights on this object, or the token lacks the scope "
        "(management actions need 'Everything (all methods)', check-in needs 'Registrants')"
    ),
    404: "not found",
}


def _describe_error(response: httpx.Response) -> str:
    detail = ""
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            detail = " - ".join(str(error[k]) for k in ("title", "message") if error.get(k))
        elif payload.get("message"):
            detail = str(payload["message"])
        else:
            detail = json.dumps(payload)[:300]
    elif response.text:
        soup = BeautifulSoup(response.text, "html.parser")
        detail = soup.title.get_text(strip=True) if soup.title else soup.get_text(" ", strip=True)[:300]
    hint = _STATUS_HINTS.get(response.status_code, "")
    return f"HTTP {response.status_code}" + (f" ({hint})" if hint else "") + (f": {detail}" if detail else "")
