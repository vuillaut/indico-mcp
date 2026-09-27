"""MCP tools for reading and managing Indico events."""

from __future__ import annotations

import json
import mimetypes
import re
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from indico_mcp.client import IndicoClient, IndicoError
from indico_mcp.config import Instance, Settings

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)

EventId = Annotated[int, Field(description="Indico event id (the number in /event/<id>/)")]
InstanceName = Annotated[
    str | None,
    Field(
        description="Indico instance: a configured name (see indico_list_instances) or its URL; an event link "
        "works too. Can be left out when only one instance is configured or a default is set."
    ),
]
LocalDateTime = Annotated[
    str,
    Field(description="Local time in the event's timezone, ISO format without offset, e.g. 2026-10-05T14:30"),
]

INSTRUCTIONS = """\
Tools for Indico. {instances}
Ids matter:
- Management tools take database ids. indico_list_contributions and indico_get_timetable
  return them (`id` / `contribution_id`). The export API's contribution `id` is the public
  number shown on the website; its database id is `db_id`.
- Timetable entries, session blocks, sessions and contributions each have their own ids.
Scheduling a session's contributions needs a session block first (indico_create_session_block).
Approving or rejecting a registration emails the registrant.
"""


class Person(BaseModel):
    """A speaker or author, entered by name; Indico links an existing account by email."""

    first_name: str = ""
    last_name: str
    email: str = ""
    affiliation: str = ""
    speaker: bool = True
    author_type: Literal["none", "primary", "secondary"] = Field(
        default="none", description="Author role; only used in conferences"
    )

    def to_indico(self, order: int) -> dict[str, Any]:
        roles = (["speaker"] if self.speaker else []) + [self.author_type]
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "affiliation": self.affiliation,
            "roles": roles,
            "display_order": order,
        }


def create_server(settings: Settings) -> MCPServer:
    http = {
        i.name: httpx.AsyncClient(base_url=i.url, timeout=settings.timeout, follow_redirects=False)
        for i in settings.instances
    }
    mcp = MCPServer(name="indico", version="0.1.0", instructions=INSTRUCTIONS.format(instances=_describe(settings)))

    def resolve(instance: str | None) -> Instance:
        return _resolve_instance(settings, instance)

    def client(ctx: Context, instance: str | None) -> IndicoClient:
        target = resolve(instance)
        token = _token_from(ctx, target.name, single=len(settings.instances) == 1) or target.token
        return IndicoClient(http[target.name], token)

    def tool(annotations: ToolAnnotations) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def register(fn: Callable[..., Any]) -> Callable[..., Any]:
            mcp.tool(annotations=annotations)(_reraise(fn))
            return fn

        return register

    # ------------------------------------------------------------------ read

    @tool(READ)
    async def indico_list_instances() -> dict[str, Any]:
        """List the Indico instances this server can reach; pass a name as `instance` to the other tools."""
        return {
            "instances": [{"name": i.name, "url": i.url, "token": i.token is not None} for i in settings.instances],
            "default": _default_name(settings),
        }

    @tool(READ)
    async def indico_whoami(ctx: Context, instance: InstanceName = None) -> dict[str, Any]:
        """Return the Indico user the token belongs to (null when anonymous)."""
        return await client(ctx, instance).get_json("/api/user/")

    @tool(READ)
    async def indico_search_events(
        ctx: Context,
        query: Annotated[str, Field(description="Words from the event title")],
        from_date: Annotated[str | None, Field(description="YYYY-MM-DD, 'today', or relative like '-30d'")] = None,
        to_date: Annotated[str | None, Field(description="YYYY-MM-DD, 'today', or relative like '+30d'")] = None,
        limit: Annotated[int, Field(ge=1, le=500)] = 50,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Search events by title. Only returns events the token's user can see."""
        results = await client(ctx, instance).export(
            f"event/search/{_path_part(query)}", **{"from": from_date, "to": to_date, "limit": limit}
        )
        return {"events": [_event_summary(e) for e in results]}

    @tool(READ)
    async def indico_list_category_events(
        ctx: Context,
        category_id: Annotated[int, Field(description="Category id; 0 is the root, covering the whole instance")],
        from_date: Annotated[str | None, Field(description="YYYY-MM-DD, 'today', or relative like '-30d'")] = "today",
        to_date: Annotated[str | None, Field(description="YYYY-MM-DD, 'today', or relative like '+30d'")] = None,
        limit: Annotated[int, Field(ge=1, le=500)] = 50,
        newest_first: bool = False,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """List events in a category (and its subcategories) within a date range."""
        results = await client(ctx, instance).export(
            f"categ/{category_id}",
            **{
                "from": from_date,
                "to": to_date,
                "limit": limit,
                "order": "start",
                "descending": "yes" if newest_first else None,
            },
        )
        return {"events": [_event_summary(e) for e in results]}

    @tool(READ)
    async def indico_get_event(
        ctx: Context,
        event_id: EventId,
        detail: Annotated[
            Literal["events", "contributions", "subcontributions", "sessions"],
            Field(description="How much to include: 'events' is metadata only"),
        ] = "contributions",
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Get an event's details: dates, location, chairs, material, and optionally contributions or sessions.

        In the contributions list, `id` is the public number and `db_id` is the id management tools need.
        """
        results = await client(ctx, instance).export(f"event/{event_id}", detail=detail)
        if not results:
            raise ToolError(f"event {event_id} not found or not visible to this user")
        event = _clean(results[0])
        return _in_zone(event, event.get("timezone"))

    @tool(READ)
    async def indico_get_timetable(ctx: Context, event_id: EventId, instance: InstanceName = None) -> dict[str, Any]:
        """Get an event's timetable as a flat list of entries in start order.

        Each entry has `entry_id` (for indico_move_timetable_entry / indico_unschedule_timetable_entry),
        and depending on its kind `contribution_id`, `session_id`, `session_block_id`, `parent_entry_id`.
        """
        results = await client(ctx, instance).export(f"timetable/{event_id}", nc="yes")
        days = (results or {}).get(str(event_id)) or {}
        entries = [
            _timetable_entry(key, raw, parent) for day in days.values() for key, raw, parent in _walk_timetable(day)
        ]
        entries.sort(key=lambda e: e["start"] or "")
        return {"event_id": event_id, "entries": entries}

    @tool(READ)
    async def indico_list_contributions(
        ctx: Context, event_id: EventId, instance: InstanceName = None
    ) -> dict[str, Any]:
        """List all contributions of an event with database ids, session, schedule and people.

        Needs management rights on the event.
        """
        raw = await client(ctx, instance).get_json(f"/event/{event_id}/manage/contributions/contributions.json")
        return {"contributions": [_contribution_summary(c) for c in raw]}

    @tool(READ)
    async def indico_list_registration_forms(
        ctx: Context, event_id: EventId, instance: InstanceName = None
    ) -> dict[str, Any]:
        """List an event's registration forms with registration counts. Needs the 'Registrants' token scope."""
        return {"forms": await client(ctx, instance).get_json(f"/api/checkin/event/{event_id}/forms/")}

    @tool(READ)
    async def indico_list_registrations(
        ctx: Context, event_id: EventId, form_id: int, instance: InstanceName = None
    ) -> dict[str, Any]:
        """List registrations of a registration form (state, payment, check-in, tags)."""
        path = f"/api/checkin/event/{event_id}/forms/{form_id}/registrations/"
        return {"registrations": await client(ctx, instance).get_json(path)}

    @tool(READ)
    async def indico_get_registration(
        ctx: Context, event_id: EventId, form_id: int, registration_id: int, instance: InstanceName = None
    ) -> dict[str, Any]:
        """Get one registration, including the answers to the form fields."""
        path = f"/api/checkin/event/{event_id}/forms/{form_id}/registrations/{registration_id}"
        return await client(ctx, instance).get_json(path)

    if settings.read_only:
        return mcp

    # ------------------------------------------------------------------ events

    @tool(WRITE)
    async def indico_create_event(
        ctx: Context,
        category_id: Annotated[int, Field(description="Category to create the event in")],
        title: str,
        start: LocalDateTime,
        end: LocalDateTime,
        timezone: Annotated[str, Field(description="IANA timezone, e.g. Europe/Zurich or Europe/Paris")],
        event_type: Literal["meeting", "conference"] = "meeting",
        venue_name: str = "",
        room_name: str = "",
        address: str = "",
        listed: Annotated[bool, Field(description="Show the event in the category listing")] = True,
        protection_mode: Literal["inheriting", "public", "protected"] = "inheriting",
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Create a meeting or conference and return its id."""
        _check_timezone(timezone)
        prefix = "event-creation-"
        overrides = {
            f"{prefix}title": title,
            f"{prefix}category": json.dumps({"id": category_id}),
            f"{prefix}start_dt": _split_local(start),
            f"{prefix}end_dt": _split_local(end),
            f"{prefix}timezone": timezone,
            f"{prefix}location_data": json.dumps(
                {"inheriting": False, "venue_name": venue_name, "room_name": room_name, "address": address}
            ),
            f"{prefix}listing": "true" if listed else "false",
            f"{prefix}protection_mode": protection_mode,
        }
        result = await client(ctx, instance).edit_form(f"/event/create/{event_type}", overrides)
        match = re.search(r"/event/(\d+)/", result.get("redirect", ""))
        event_id = int(match.group(1)) if match else None
        return {"event_id": event_id, "url": f"{resolve(instance).url}/event/{event_id}/" if event_id else None}

    @tool(WRITE)
    async def indico_update_event(
        ctx: Context,
        event_id: EventId,
        title: str | None = None,
        description: Annotated[str | None, Field(description="HTML allowed")] = None,
        start: LocalDateTime | None = None,
        end: LocalDateTime | None = None,
        timezone: Annotated[str | None, Field(description="IANA timezone")] = None,
        venue_name: str | None = None,
        room_name: str | None = None,
        address: str | None = None,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Change an event's title, description, dates or location. Fields left out keep their value.

        Changing dates also shifts the timetable, as the Indico UI does by default.
        """
        indico = client(ctx, instance)
        base = f"/event/{event_id}/manage/settings"
        changed: list[str] = []

        data = _drop_none({"title": title, "description": description})
        if data:
            await indico.edit_form(f"{base}/data", data)
            changed += data

        dates = _drop_none(
            {
                "start_dt": _split_local(start) if start else None,
                "end_dt": _split_local(end) if end else None,
                "timezone": timezone and _check_timezone(timezone),
            }
        )
        if dates:
            await indico.edit_form(f"{base}/dates", dates)
            changed += dates

        location = _drop_none({"venue_name": venue_name, "room_name": room_name, "address": address})
        if location:
            form = await indico.get_form(f"{base}/location")
            current = json.loads((form.get("location_data") or ["{}"])[0] or "{}")
            await indico.submit_form(
                f"{base}/location", form.merged({"location_data": json.dumps(_merge_location(current, location))})
            )
            changed += location

        if not changed:
            raise ToolError("nothing to change: pass at least one field")
        return {"event_id": event_id, "updated": changed}

    # ------------------------------------------------------------------ sessions

    @tool(WRITE)
    async def indico_create_session(
        ctx: Context,
        event_id: EventId,
        title: str,
        description: str | None = None,
        code: Annotated[str | None, Field(description="Book of abstracts code; conferences only")] = None,
        default_contribution_minutes: int | None = None,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Create a session. It has no time slot until you add one with indico_create_session_block."""
        overrides = _drop_none(
            {
                "title": title,
                "description": description,
                "code": code,
                "default_contribution_duration": _seconds(default_contribution_minutes),
            }
        )
        result = await client(ctx, instance).edit_form(f"/event/{event_id}/manage/sessions/create", overrides)
        return {"session_id": result.get("new_session_id")}

    @tool(WRITE)
    async def indico_update_session(
        ctx: Context,
        event_id: EventId,
        session_id: int,
        title: str | None = None,
        description: str | None = None,
        code: str | None = None,
        default_contribution_minutes: int | None = None,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Change a session's title, description, code or default contribution length."""
        overrides = _drop_none(
            {
                "title": title,
                "description": description,
                "code": code,
                "default_contribution_duration": _seconds(default_contribution_minutes),
            }
        )
        if not overrides:
            raise ToolError("nothing to change: pass at least one field")
        await client(ctx, instance).edit_form(f"/event/{event_id}/manage/sessions/{session_id}/modify", overrides)
        return {"session_id": session_id, "updated": list(overrides)}

    @tool(WRITE)
    async def indico_create_session_block(
        ctx: Context,
        event_id: EventId,
        session_id: int,
        start: LocalDateTime,
        duration_minutes: Annotated[int, Field(ge=1)],
        title: Annotated[str, Field(description="Optional block title, e.g. 'Part 1'")] = "",
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Add a time slot (session block) for a session to the timetable; contributions of the session go inside it."""
        day, time = _split_local(start)
        overrides = {"time": time, "duration": _seconds(duration_minutes), "title": title}
        result = await client(ctx, instance).edit_form(
            f"/event/{event_id}/manage/timetable/add-session-block",
            overrides,
            params={"parent_session_id": session_id, "day": day},
        )
        # `update.entry` is the new block; the rest of `update` re-serializes the whole day
        update = result.get("update") or {}
        entry = update.get("entry") or {}
        return {
            "session_block_id": entry.get("sessionSlotId"),
            "entry_id": _entry_number(update.get("id") or entry.get("id")),
        }

    @tool(WRITE)
    async def indico_update_session_block(
        ctx: Context,
        event_id: EventId,
        entry_id: Annotated[int, Field(description="The block's timetable entry id (see indico_get_timetable)")],
        duration_minutes: Annotated[int | None, Field(ge=1)] = None,
        title: str | None = None,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Change a session block's duration or title. It cannot become shorter than the entries inside it."""
        overrides = _drop_none({"duration": _seconds(duration_minutes), "title": title})
        if not overrides:
            raise ToolError("nothing to change: pass at least one field")
        result = await client(ctx, instance).edit_form(
            f"/event/{event_id}/manage/timetable/entry/{entry_id}/edit/", overrides
        )
        entry = (result.get("update") or {}).get("entry") or {}
        # report where the block ended up so an unexpected shift is visible
        return {
            "entry_id": entry_id,
            "updated": list(overrides),
            "start": _export_dt(entry.get("startDate")),
            "end": _export_dt(entry.get("endDate")),
        }

    # ------------------------------------------------------------------ contributions

    @tool(WRITE)
    async def indico_create_contribution(
        ctx: Context,
        event_id: EventId,
        title: str,
        description: str | None = None,
        duration_minutes: int | None = None,
        persons: list[Person] | None = None,
        session_id: Annotated[int | None, Field(description="Assign to this session right away")] = None,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Create an unscheduled contribution. Use indico_schedule_contribution to place it in the timetable."""
        indico = client(ctx, instance)
        overrides = _drop_none(
            {
                "title": title,
                "description": description,
                "duration": _seconds(duration_minutes),
                "person_link_data": _persons_json(persons),
            }
        )
        await indico.edit_form(f"/event/{event_id}/manage/contributions/create", overrides)
        # the response only carries rendered HTML, so look the new id up
        listing = await indico.get_json(f"/event/{event_id}/manage/contributions/contributions.json")
        ids = [c["id"] for c in listing if c.get("title") == title]
        contribution_id = max(ids) if ids else None
        if contribution_id and session_id is not None:
            await indico.rest(
                "PATCH", f"/event/{event_id}/manage/contributions/{contribution_id}", {"session_id": session_id}
            )
        return {"contribution_id": contribution_id, "session_id": session_id}

    @tool(WRITE)
    async def indico_update_contribution(
        ctx: Context,
        event_id: EventId,
        contribution_id: Annotated[int, Field(description="Database id (see indico_list_contributions)")],
        title: str | None = None,
        description: str | None = None,
        duration_minutes: int | None = None,
        persons: Annotated[
            list[Person] | None,
            Field(description="Replaces the whole list of speakers/authors when given"),
        ] = None,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Change a contribution's title, description, duration or people. Fields left out keep their value."""
        overrides = _drop_none(
            {
                "title": title,
                "description": description,
                "duration": _seconds(duration_minutes),
                "person_link_data": _persons_json(persons),
            }
        )
        if not overrides:
            raise ToolError("nothing to change: pass at least one field")
        await client(ctx, instance).edit_form(
            f"/event/{event_id}/manage/contributions/{contribution_id}/edit", overrides
        )
        return {"contribution_id": contribution_id, "updated": list(overrides)}

    @tool(WRITE)
    async def indico_assign_contribution_session(
        ctx: Context,
        event_id: EventId,
        contribution_id: int,
        session_id: Annotated[int | None, Field(description="null removes the contribution from its session")],
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Move a contribution into a session, or out of it. Indico may unschedule it if its slot no longer fits."""
        result = await client(ctx, instance).rest(
            "PATCH", f"/event/{event_id}/manage/contributions/{contribution_id}", {"session_id": session_id}
        )
        return {"contribution_id": contribution_id, "session_id": session_id, **(result or {})}

    # ------------------------------------------------------------------ timetable

    @tool(WRITE)
    async def indico_schedule_contribution(
        ctx: Context,
        event_id: EventId,
        contribution_id: int,
        start: LocalDateTime,
        session_block_id: Annotated[
            int | None,
            Field(description="Put it inside this session block; required if the contribution is in a session"),
        ] = None,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Put an unscheduled contribution in the timetable at a given time."""
        indico = client(ctx, instance)
        body: dict[str, Any] = {
            "contribution_id": contribution_id,
            "start_dt": await _event_datetime(indico, event_id, start),
        }
        if session_block_id is not None:
            body["session_block_id"] = session_block_id
        result = await indico.rest("POST", f"/event/{event_id}/manage/timetable/", body)
        return {"entry_id": result.get("id"), "start": result.get("start_dt")}

    @tool(WRITE)
    async def indico_move_timetable_entry(
        ctx: Context, event_id: EventId, entry_id: int, start: LocalDateTime, instance: InstanceName = None
    ) -> dict[str, Any]:
        """Change the start time of a timetable entry (contribution or session block)."""
        indico = client(ctx, instance)
        start_dt = await _event_datetime(indico, event_id, start)
        await indico.rest("PATCH", f"/event/{event_id}/manage/timetable/{entry_id}", {"start_dt": start_dt})
        return {"entry_id": entry_id, "start": start_dt}

    @tool(DESTRUCTIVE)
    async def indico_unschedule_timetable_entry(
        ctx: Context, event_id: EventId, entry_id: int, instance: InstanceName = None
    ) -> dict[str, Any]:
        """Remove an entry from the timetable.

        In a conference, a contribution goes back to the unscheduled list. Anything else deletes data:
        in meetings the contribution itself is deleted, and a session block is deleted with its schedule.
        Those cases are refused unless the server runs with INDICO_ALLOW_DELETE=true.
        """
        indico = client(ctx, instance)
        event = (await indico.export(f"event/{event_id}", detail="events"))[0]
        days = ((await indico.export(f"timetable/{event_id}", nc="yes")) or {}).get(str(event_id)) or {}
        kind = next(
            (
                raw.get("entryType")
                for day in days.values()
                for key, raw, _ in _walk_timetable(day)
                if _entry_number(key) == entry_id
            ),
            None,
        )
        if kind is None:
            raise ToolError(f"entry {entry_id} is not in the timetable of event {event_id}")
        deletes_data = not (kind == "Contribution" and event.get("type") == "conference")
        if deletes_data and not settings.allow_delete:
            raise ToolError(
                f"removing this {kind.lower()} entry from a {event.get('type')} deletes data, and deletes are "
                "disabled on this server (INDICO_ALLOW_DELETE)"
            )
        await indico.rest("DELETE", f"/event/{event_id}/manage/timetable/{entry_id}")
        return {"entry_id": entry_id, "removed": True, "deleted_data": deletes_data}

    # ------------------------------------------------------------------ attachments

    def attachments_path(event_id: int, contribution_id: int | None, session_id: int | None) -> str:
        if contribution_id is not None and session_id is not None:
            raise ToolError("pass contribution_id or session_id, not both")
        if contribution_id is not None:
            return f"/event/{event_id}/manage/contributions/{contribution_id}/attachments"
        if session_id is not None:
            return f"/event/{event_id}/manage/sessions/{session_id}/attachments"
        return f"/event/{event_id}/manage/attachments"

    @tool(WRITE)
    async def indico_add_link(
        ctx: Context,
        event_id: EventId,
        url: str,
        title: str,
        contribution_id: Annotated[int | None, Field(description="Attach to this contribution")] = None,
        session_id: Annotated[int | None, Field(description="Attach to this session")] = None,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Attach a link (slides, recording, document) to an event, a session or a contribution."""
        path = attachments_path(event_id, contribution_id, session_id) + "/add/link"
        await client(ctx, instance).edit_form(path, {"title": title, "link_url": url})
        return {"attached": True, "title": title, "url": url}

    if settings.upload_dir is not None:
        upload_dir = settings.upload_dir

        async def indico_upload_file(
            ctx: Context,
            event_id: EventId,
            file_path: Annotated[str, Field(description="Path of the file, inside the upload directory")],
            contribution_id: Annotated[int | None, Field(description="Attach to this contribution")] = None,
            session_id: Annotated[int | None, Field(description="Attach to this session")] = None,
            instance: InstanceName = None,
        ) -> dict[str, Any]:
            path = Path(file_path).expanduser()
            resolved = (path if path.is_absolute() else upload_dir / path).resolve()
            if not resolved.is_relative_to(upload_dir):
                raise ToolError(f"file must be inside {upload_dir}")
            if not resolved.is_file():
                raise ToolError(f"no such file: {resolved}")
            indico = client(ctx, instance)
            url = attachments_path(event_id, contribution_id, session_id) + "/add/files"
            form = await indico.get_form(url)
            content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
            files = [("files", (resolved.name, resolved.read_bytes(), content_type))]
            await indico.submit_form(url, form.merged({}), files=files)
            return {"uploaded": resolved.name}

        indico_upload_file.__doc__ = (
            f"Upload a file as material of an event, a session or a contribution. "
            f"Only files inside {upload_dir} can be uploaded."
        )
        tool(WRITE)(indico_upload_file)

    # ------------------------------------------------------------------ registrations

    @tool(WRITE)
    async def indico_set_checkin(
        ctx: Context,
        event_id: EventId,
        form_id: int,
        registration_id: int,
        checked_in: bool,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Mark a registrant as checked in at the venue, or undo it."""
        path = f"/api/checkin/event/{event_id}/forms/{form_id}/registrations/{registration_id}"
        return await client(ctx, instance).rest("PATCH", path, {"checked_in": checked_in})

    @tool(WRITE)
    async def indico_moderate_registration(
        ctx: Context,
        event_id: EventId,
        form_id: int,
        registration_id: int,
        action: Literal["approve", "reject"],
        reason: Annotated[str, Field(description="Rejection reason, kept in Indico")] = "",
        send_reason: Annotated[bool, Field(description="Include the reason in the rejection email")] = False,
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Approve or reject a pending registration. Indico emails the registrant either way."""
        indico = client(ctx, instance)
        base = f"/event/{event_id}/manage/registration/{form_id}/registrations/{registration_id}"
        if action == "approve":
            await indico.submit_form(f"{base}/approve", [])
        else:
            overrides: dict[str, Any] = {"rejection_reason": reason}
            if send_reason:
                overrides["attach_rejection_reason"] = "y"
            await indico.edit_form(f"{base}/reject", overrides)
        return {"registration_id": registration_id, "action": action}

    if not settings.allow_delete:
        return mcp

    # ------------------------------------------------------------------ deletes

    @tool(DESTRUCTIVE)
    async def indico_delete_contribution(
        ctx: Context, event_id: EventId, contribution_id: int, instance: InstanceName = None
    ) -> dict[str, Any]:
        """Delete a contribution, with its timetable entry and material."""
        await client(ctx, instance).rest("DELETE", f"/event/{event_id}/manage/contributions/{contribution_id}")
        return {"contribution_id": contribution_id, "deleted": True}

    @tool(DESTRUCTIVE)
    async def indico_delete_session(
        ctx: Context, event_id: EventId, session_id: int, instance: InstanceName = None
    ) -> dict[str, Any]:
        """Delete a session and its blocks. Its contributions stay, unscheduled and without a session."""
        await client(ctx, instance).rest("DELETE", f"/event/{event_id}/manage/sessions/{session_id}")
        return {"session_id": session_id, "deleted": True}

    @tool(DESTRUCTIVE)
    async def indico_delete_event(
        ctx: Context,
        event_id: EventId,
        confirm_title: Annotated[str, Field(description="The event's exact title, as a safety check")],
        instance: InstanceName = None,
    ) -> dict[str, Any]:
        """Delete a whole event. Only an Indico admin can restore it."""
        indico = client(ctx, instance)
        event = (await indico.export(f"event/{event_id}", detail="events"))[0]
        if event.get("title") != confirm_title:
            raise ToolError(f"confirm_title does not match the event title {event.get('title')!r}")
        await indico.submit_form(f"/event/{event_id}/manage/delete", [])
        return {"event_id": event_id, "deleted": True}

    return mcp


# ---------------------------------------------------------------------- helpers


def _describe(settings: Settings) -> str:
    names = ", ".join(f"{i.name} ({i.url})" for i in settings.instances)
    if len(settings.instances) == 1:
        return f"This server talks to {names}."
    default = _default_name(settings)
    choice = f"The default is {default}." if default else "Every tool needs the `instance` argument."
    return f"This server talks to several instances: {names}. {choice}"


def _default_name(settings: Settings) -> str | None:
    if len(settings.instances) == 1:
        return settings.instances[0].name
    return settings.default


def _resolve_instance(settings: Settings, value: str | None) -> Instance:
    """Find an instance by name, host, or any URL on that host."""
    if value is None or not value.strip():
        name = _default_name(settings)
        if name is None:
            raise ToolError(f"pass `instance`, one of {[i.name for i in settings.instances]}")
        value = name
    value = value.strip().lower()
    host = urlsplit(value if "//" in value else f"//{value}").hostname
    for instance in settings.instances:
        if value == instance.name or host == instance.host:
            return instance
    raise ToolError(
        f"unknown instance {value!r}; configured: " + ", ".join(f"{i.name} ({i.url})" for i in settings.instances)
    )


def _token_from(ctx: Context, instance: str, single: bool) -> str | None:
    """Per-request token for HTTP deployments.

    X-Indico-Token-<name> is always honored. X-Indico-Token and Authorization: Bearer are only
    used when the server has a single instance, so a token never reaches another Indico.
    """
    headers = ctx.headers
    if not headers:
        return None
    if token := headers.get(f"x-indico-token-{instance.replace('_', '-')}"):
        return token.strip()
    if not single:
        return None
    if token := headers.get("x-indico-token"):
        return token.strip()
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def _reraise(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Turn IndicoError into ToolError so the agent sees the message."""
    import functools

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await fn(*args, **kwargs)
        except IndicoError as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


def _path_part(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")


def _drop_none(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None}


def _seconds(minutes: int | None) -> str | None:
    return None if minutes is None else str(minutes * 60)


def _parse_local(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.strip().replace(" ", "T"))
    except ValueError as exc:
        raise ToolError(f"invalid datetime {value!r}; use e.g. 2026-10-05T14:30") from exc
    return dt


def _split_local(value: str) -> list[str]:
    """Indico's datetime form fields take the date and the time as two values."""
    dt = _parse_local(value)
    if dt.tzinfo is not None:
        raise ToolError(f"{value!r}: give the local time in the event's timezone, without an offset")
    return [dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")]


def _check_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except Exception as exc:
        raise ToolError(f"unknown timezone {name!r}") from exc
    return name


async def _event_datetime(indico: IndicoClient, event_id: int, value: str) -> str:
    """ISO datetime with offset; naive input is read in the event's timezone."""
    dt = _parse_local(value)
    if dt.tzinfo is None:
        event = (await indico.export(f"event/{event_id}", detail="events"))[0]
        dt = dt.replace(tzinfo=ZoneInfo(event["timezone"]))
    return dt.isoformat()


def _merge_location(current: dict[str, Any], changes: dict[str, str]) -> dict[str, Any]:
    location = {**current, **changes, "inheriting": False}
    # an id points at a room/venue from room booking and wins over the name
    if "room_name" in changes:
        location.pop("room_id", None)
    if "venue_name" in changes:
        location.pop("venue_id", None)
        location.pop("room_id", None)
    return location


def _persons_json(persons: list[Person] | None) -> str | None:
    if persons is None:
        return None
    return json.dumps([p.to_indico(i) for i, p in enumerate(persons)])


def _clean(value: Any) -> Any:
    """Drop the export API's internal `_fossil` markers."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if k != "_fossil"}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _export_dt(value: Any, zone: str | None = None) -> str | None:
    """`{date, time, tz}` from the export API as a local ISO string, converted to `zone` if given."""
    if isinstance(value, dict) and value.get("date"):
        value = _convert(value, zone)
        return f"{value['date']}T{value.get('time', '00:00:00')}"
    return value


def _convert(value: dict[str, Any], zone: str | None) -> dict[str, Any]:
    """The event and category exports use the server's timezone, not the event's; move to `zone`."""
    if not zone or not value.get("tz") or value["tz"] == zone:
        return value
    try:
        source = datetime.fromisoformat(f"{value['date']}T{value.get('time', '00:00:00')}")
        local = source.replace(tzinfo=ZoneInfo(value["tz"])).astimezone(ZoneInfo(zone))
    except (ValueError, KeyError, ZoneInfoNotFoundError):
        return value
    return {**value, "date": local.strftime("%Y-%m-%d"), "time": local.strftime("%H:%M:%S"), "tz": zone}


def _in_zone(value: Any, zone: str | None) -> Any:
    """Convert every `{date, time, tz}` in an export payload to `zone`."""
    if isinstance(value, dict):
        if "date" in value and "tz" in value:
            return _convert(value, zone)
        return {k: _in_zone(v, zone) for k, v in value.items()}
    if isinstance(value, list):
        return [_in_zone(v, zone) for v in value]
    return value


def _event_summary(event: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "id": int(event["id"]),
        "title": event.get("title"),
        "type": event.get("type"),
        "start": _export_dt(event.get("startDate"), event.get("timezone")),
        "end": _export_dt(event.get("endDate"), event.get("timezone")),
        # the search export has no event timezone and gives times in UTC
        "timezone": event.get("timezone") or (event.get("startDate") or {}).get("tz"),
        "category": event.get("category"),
        "category_id": event.get("categoryId"),
        "location": event.get("location"),
        "room": event.get("room"),
        "url": event.get("url"),
    }
    return {k: v for k, v in summary.items() if v is not None}


def _entry_number(key: Any) -> int | None:
    """Timetable keys look like 's123' / 'c456' / 'b789'; the number is the entry id."""
    match = re.fullmatch(r"[scb]?(\d+)", str(key or ""))
    return int(match.group(1)) if match else None


def _walk_timetable(entries: dict[str, Any], parent: str | None = None) -> Iterator[tuple[str, dict, str | None]]:
    for key, raw in (entries or {}).items():
        yield key, raw, parent
        yield from _walk_timetable(raw.get("entries") or {}, key)


def _timetable_entry(key: str, raw: dict[str, Any], parent: str | None) -> dict[str, Any]:
    kind = {"Session": "session_block"}.get(raw.get("entryType"), (raw.get("entryType") or "").lower())
    entry = {
        "entry_id": _entry_number(key),
        "kind": kind,
        "title": raw.get("slotTitle") or raw.get("title") if kind == "session_block" else raw.get("title"),
        "start": _export_dt(raw.get("startDate")),
        "end": _export_dt(raw.get("endDate")),
        "duration_minutes": raw.get("duration"),
        "parent_entry_id": _entry_number(parent),
        "room": raw.get("room") or None,
    }
    if kind == "session_block":
        entry |= {
            "session_id": raw.get("sessionId"),
            "session_block_id": raw.get("sessionSlotId"),
            "session_title": raw.get("title"),
        }
    elif kind == "contribution":
        entry |= {
            "contribution_id": raw.get("contributionId"),
            "public_id": raw.get("friendlyId"),
            "session_id": raw.get("sessionId"),
            "session_block_id": raw.get("sessionSlotId"),
            "speakers": [p.get("name") for p in raw.get("presenters") or [] if p.get("name")],
        }
    return entry


def _contribution_summary(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": c.get("id"),
        "public_id": c.get("friendly_id"),
        "title": c.get("title"),
        "code": c.get("code") or None,
        "start": c.get("start_dt"),
        "end": c.get("end_dt"),
        "duration_minutes": round(c["duration"] / 60) if isinstance(c.get("duration"), (int, float)) else None,
        "session": c.get("session"),
        "session_block": c.get("session_block"),
        "track": c.get("track"),
        "type": c.get("type"),
        "persons": [
            {k: p.get(k) for k in ("first_name", "last_name", "email", "affiliation", "is_speaker", "author_type")}
            for p in c.get("persons") or []
        ],
    }
