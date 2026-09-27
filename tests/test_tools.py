import json
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
import respx
from mcp.client.client import Client

from indico_mcp.config import Instance, Settings
from indico_mcp.server import create_server

BASE = "https://indico.example.org"


def form_json(inner: str) -> dict:
    return {"html": f"<form>{inner}</form>", "js": ""}


def posted(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(request.content.decode(), keep_blank_values=True)


async def call(settings: Settings, name: str, **args):
    async with Client(create_server(settings)) as client:
        result = await client.call_tool(name, args)
    text = result.content[0].text if result.content else ""
    return result.is_error, (json.loads(text) if not result.is_error else text)


@pytest.fixture
def settings():
    return Settings.single(BASE, "indp_test")


@respx.mock
async def test_update_contribution_keeps_untouched_fields(settings):
    path = "/event/5/manage/contributions/9/edit"
    respx.get(BASE + path).respond(
        json=form_json(
            '<input type="hidden" name="title" value="Old">'
            '<textarea name="description">Abstract</textarea>'
            '<input type="hidden" name="duration" value="1200">'
            '<input type="hidden" name="person_link_data" value="[{&quot;last_name&quot;: &quot;Curie&quot;}]">'
            '<input type="checkbox" name="board_number_enabled" value="y" checked>'
        )
    )
    post = respx.post(BASE + path).respond(json={"success": True})

    is_error, result = await call(settings, "indico_update_contribution", event_id=5, contribution_id=9, title="New")

    assert not is_error, result
    body = posted(post.calls.last.request)
    assert body["title"] == ["New"]
    assert body["description"] == ["Abstract"]
    assert body["person_link_data"] == ['[{"last_name": "Curie"}]']
    assert body["board_number_enabled"] == ["y"]
    request = post.calls.last.request
    assert request.headers["authorization"] == "Bearer indp_test"
    assert request.headers["x-requested-with"] == "XMLHttpRequest"


@respx.mock
async def test_form_errors_reach_the_agent(settings):
    path = "/event/5/manage/sessions/create"
    respx.get(BASE + path).respond(json=form_json('<input name="title" value="">'))  # meetings have no code field
    respx.post(BASE + path).respond(
        json=form_json('<div data-error="&lt;li&gt;Title is required&lt;/li&gt;"><input name="title" value=""></div>')
    )
    is_error, message = await call(settings, "indico_create_session", event_id=5, title=" ")
    assert is_error
    assert "title: Title is required" in message


@respx.mock
async def test_unknown_field_is_refused_instead_of_guessed(settings):
    path = "/event/5/manage/sessions/3/modify"
    respx.get(BASE + path).respond(json=form_json('<input name="title" value="S">'))
    post = respx.post(BASE + path)
    is_error, message = await call(settings, "indico_update_session", event_id=5, session_id=3, code="A1")
    assert is_error and "has no field(s) ['code']" in message
    assert not post.called


@respx.mock
async def test_create_event_splits_dates_and_returns_id(settings):
    path = "/event/create/conference"
    p = "event-creation-"
    respx.get(BASE + path).respond(
        json=form_json(
            f'<input name="{p}title" value=""><input name="{p}category" value="">'
            f'<input name="{p}start_dt" value=""><input name="{p}start_dt" value="">'
            f'<input name="{p}end_dt" value=""><input name="{p}end_dt" value="">'
            f'<select name="{p}timezone"><option value="UTC" selected>UTC</option></select>'
            f'<input name="{p}location_data" value="{{}}"><input name="{p}listing" value="true">'
            f'<input type="radio" name="{p}protection_mode" value="inheriting" checked>'
            f'<input type="hidden" name="{p}create_booking" value="false">'
        )
    )
    post = respx.post(BASE + path).respond(json={"success": True, "redirect": "/event/4242/manage/"})

    is_error, result = await call(
        settings,
        "indico_create_event",
        category_id=12,
        title="Workshop",
        start="2026-11-02T09:00",
        end="2026-11-04T17:30",
        timezone="Europe/Paris",
        event_type="conference",
        venue_name="LAPP",
    )

    assert not is_error, result
    assert result == {"event_id": 4242, "url": f"{BASE}/event/4242/"}
    body = posted(post.calls.last.request)
    assert body[f"{p}start_dt"] == ["2026-11-02", "09:00"]
    assert body[f"{p}end_dt"] == ["2026-11-04", "17:30"]
    assert body[f"{p}timezone"] == ["Europe/Paris"]
    assert json.loads(body[f"{p}category"][0]) == {"id": 12}
    assert json.loads(body[f"{p}location_data"][0])["venue_name"] == "LAPP"
    assert body[f"{p}create_booking"] == ["false"]


async def test_datetime_with_offset_is_rejected(settings):
    is_error, message = await call(
        settings,
        "indico_create_session_block",
        event_id=1,
        session_id=2,
        start="2026-11-02T09:00+01:00",
        duration_minutes=60,
    )
    assert is_error and "without an offset" in message


@respx.mock
async def test_create_session_block_reports_the_new_block(settings):
    path = "/event/5/manage/timetable/add-session-block"
    respx.get(BASE + path).respond(
        json=form_json('<input name="title" value=""><input name="time" value=""><input name="duration" value="">')
    )
    # Indico also re-serializes the whole day; its other entries (here a break) must not be picked
    day = {"b10": {"id": "b10", "entryType": "Break", "sessionSlotId": None}}
    new_block = {"id": "s42", "entryType": "Session", "sessionSlotId": 7}
    respx.post(BASE + path).respond(
        json={"success": True, "update": {"id": "s42", "entry": new_block, "day": "20261116", "entries": day}}
    )

    is_error, result = await call(
        settings,
        "indico_create_session_block",
        event_id=5,
        session_id=3,
        start="2026-11-16T11:00",
        duration_minutes=80,
    )

    assert not is_error, result
    assert result == {"session_block_id": 7, "entry_id": 42}


@respx.mock
async def test_update_session_block_keeps_untouched_fields(settings):
    path = "/event/5/manage/timetable/entry/42/edit/"
    fields = '<input name="title" value="P1"><input name="time" value="10:00"><input name="duration" value="1200">'
    respx.get(BASE + path).respond(json=form_json(fields))
    entry = {
        "startDate": {"date": "2026-11-17", "time": "10:00:00", "tz": "Europe/Paris"},
        "endDate": {"date": "2026-11-17", "time": "10:30:00", "tz": "Europe/Paris"},
    }
    post = respx.post(BASE + path).respond(json={"success": True, "update": {"entry": entry}})

    is_error, result = await call(settings, "indico_update_session_block", event_id=5, entry_id=42, duration_minutes=30)

    assert not is_error, result
    assert result["updated"] == ["duration"]
    assert (result["start"], result["end"]) == ("2026-11-17T10:00:00", "2026-11-17T10:30:00")
    body = posted(post.calls.last.request)
    assert body == {"title": ["P1"], "time": ["10:00"], "duration": ["1800"]}


@respx.mock
async def test_get_timetable_bypasses_export_cache(settings):
    route = respx.get(BASE + "/export/timetable/7.json").respond(json=timetable(7, "s11", "Session"))

    is_error, result = await call(settings, "indico_get_timetable", event_id=7)

    assert not is_error, result
    assert route.calls.last.request.url.params["nc"] == "yes"


@respx.mock
async def test_create_contribution_finds_new_id_and_assigns_session(settings):
    path = "/event/5/manage/contributions/create"
    respx.get(BASE + path).respond(
        json=form_json(
            '<input name="title" value=""><input name="duration" value="1200">'
            '<input name="person_link_data" value="[]"><textarea name="description"></textarea>'
        )
    )
    post = respx.post(BASE + path).respond(json={"success": True, "html": "..."})
    respx.get(BASE + "/event/5/manage/contributions/contributions.json").respond(
        json=[{"id": 70, "title": "Talk"}, {"id": 81, "title": "Talk"}, {"id": 90, "title": "Other"}]
    )
    patch = respx.patch(BASE + "/event/5/manage/contributions/81").respond(json={"unscheduled": False})

    is_error, result = await call(
        settings,
        "indico_create_contribution",
        event_id=5,
        title="Talk",
        duration_minutes=15,
        persons=[{"first_name": "Marie", "last_name": "Curie", "email": "marie@example.org"}],
        session_id=3,
    )

    assert not is_error, result
    assert result == {"contribution_id": 81, "session_id": 3}
    body = posted(post.calls.last.request)
    assert body["duration"] == ["900"]
    person = json.loads(body["person_link_data"][0])[0]
    assert person["last_name"] == "Curie" and person["roles"] == ["speaker", "none"]
    assert json.loads(patch.calls.last.request.content) == {"session_id": 3}


def timetable(event_id: int, key: str, entry_type: str) -> dict:
    return {"results": {str(event_id): {"20261102": {key: {"entryType": entry_type, "entries": {}}}}}}


@respx.mock
@pytest.mark.parametrize(
    ("event_type", "key", "entry_type", "allow_delete", "deleted"),
    [
        ("conference", "c11", "Contribution", False, True),
        ("meeting", "c11", "Contribution", False, False),
        ("conference", "s11", "Session", False, False),
        ("meeting", "c11", "Contribution", True, True),
    ],
)
async def test_unschedule_guards_data_loss(event_type, key, entry_type, allow_delete, deleted):
    settings = Settings.single(BASE, token="t", allow_delete=allow_delete)
    respx.get(BASE + "/export/event/7.json").respond(json={"results": [{"type": event_type, "timezone": "UTC"}]})
    respx.get(BASE + "/export/timetable/7.json").respond(json=timetable(7, key, entry_type))
    delete = respx.delete(BASE + "/event/7/manage/timetable/11").respond(json={})

    is_error, _ = await call(settings, "indico_unschedule_timetable_entry", event_id=7, entry_id=11)

    assert is_error is not deleted
    assert delete.called is deleted


@respx.mock
async def test_schedule_uses_event_timezone_for_local_times(settings):
    respx.get(BASE + "/export/event/7.json").respond(json={"results": [{"timezone": "Europe/Zurich"}]})
    post = respx.post(BASE + "/event/7/manage/timetable/").respond(json={"id": 99, "start_dt": "x"})
    is_error, result = await call(
        settings,
        "indico_schedule_contribution",
        event_id=7,
        contribution_id=3,
        start="2026-07-01T10:00",
        session_block_id=4,
    )
    assert not is_error, result
    assert json.loads(post.calls.last.request.content) == {
        "contribution_id": 3,
        "start_dt": "2026-07-01T10:00:00+02:00",
        "session_block_id": 4,
    }


async def test_upload_refuses_files_outside_upload_dir(tmp_path: Path):
    (tmp_path / "inside").mkdir()
    (tmp_path / "secret.txt").write_text("no")
    settings = Settings.single(BASE, token="t", upload_dir=(tmp_path / "inside").resolve())
    is_error, message = await call(settings, "indico_upload_file", event_id=1, file_path="../secret.txt")
    assert is_error and "must be inside" in message


async def test_read_only_and_delete_flags_control_the_tool_list():
    async def names(**kw):
        async with Client(create_server(Settings.single(BASE, **kw))) as client:
            return {t.name for t in (await client.list_tools()).tools}

    read_only = await names(read_only=True)
    default = await names()
    with_delete = await names(allow_delete=True)
    assert not any(n.startswith(("indico_create", "indico_update", "indico_delete")) for n in read_only)
    assert "indico_create_event" in default and "indico_delete_event" not in default
    assert {"indico_delete_event", "indico_delete_contribution", "indico_delete_session"} <= with_delete
    assert "indico_upload_file" not in with_delete  # needs INDICO_UPLOAD_DIR


@respx.mock
async def test_indico_json_errors_are_readable(settings):
    respx.get(BASE + "/api/checkin/event/5/forms/").respond(
        403, json={"error": {"title": "Access Denied", "message": "You cannot manage this event"}}
    )
    is_error, message = await call(settings, "indico_list_registration_forms", event_id=5)
    assert is_error
    assert "HTTP 403" in message and "Access Denied - You cannot manage this event" in message


CERN = "https://indico.cern.ch"
HD = "https://indico.physi.uni-heidelberg.de"


def two_instances(**kw) -> Settings:
    return Settings(
        instances=(Instance("cern", CERN, "indp_cern"), Instance("heidelberg", HD, "indp_hd")),
        **kw,
    )


@respx.mock
@pytest.mark.parametrize(
    "instance", ["heidelberg", "HEIDELBERG", HD, f"{HD}/event/42/", "indico.physi.uni-heidelberg.de"]
)
async def test_instance_picks_host_and_token(instance):
    cern = respx.get(CERN + "/api/user/").respond(json={"id": 1})
    hd = respx.get(HD + "/api/user/").respond(json={"id": 2})

    is_error, result = await call(two_instances(), "indico_whoami", instance=instance)

    assert not is_error, result
    assert result == {"id": 2}
    assert not cern.called
    assert hd.calls.last.request.headers["authorization"] == "Bearer indp_hd"


async def test_instance_is_required_without_default():
    is_error, message = await call(two_instances(), "indico_whoami")
    assert is_error and "pass `instance`" in message and "heidelberg" in message


async def test_unknown_instance_lists_the_configured_ones():
    is_error, message = await call(two_instances(), "indico_whoami", instance="https://indico.in2p3.fr")
    assert is_error and "unknown instance" in message and CERN in message


@respx.mock
async def test_default_instance_is_used_when_left_out():
    route = respx.get(CERN + "/api/user/").respond(json={"id": 1})
    is_error, _ = await call(two_instances(default="cern"), "indico_whoami")
    assert not is_error and route.called


@respx.mock
async def test_create_event_url_uses_the_instance():
    path = "/event/create/meeting"
    names = ["title", "category", "start_dt", "end_dt", "timezone", "location_data", "listing", "protection_mode"]
    respx.get(HD + path).respond(json=form_json("".join(f'<input name="event-creation-{n}" value="">' for n in names)))
    respx.post(HD + path).respond(json={"success": True, "redirect": "/event/7/manage/"})
    is_error, result = await call(
        two_instances(),
        "indico_create_event",
        instance="heidelberg",
        category_id=1,
        title="T",
        start="2026-11-02T09:00",
        end="2026-11-02T10:00",
        timezone="Europe/Berlin",
    )
    assert not is_error, result
    assert result == {"event_id": 7, "url": f"{HD}/event/7/"}


def test_instances_from_env(monkeypatch):
    monkeypatch.setenv("INDICO_INSTANCES", f"cern={CERN}, heidelberg={HD}/")
    monkeypatch.setenv("INDICO_TOKEN_HEIDELBERG", "indp_hd")
    monkeypatch.setenv("INDICO_DEFAULT_INSTANCE", "Heidelberg")
    settings = Settings.from_env()
    assert settings.instances == (Instance("cern", CERN, None), Instance("heidelberg", HD, "indp_hd"))
    assert settings.default == "heidelberg"


def test_single_url_from_env_still_works(monkeypatch):
    monkeypatch.delenv("INDICO_INSTANCES", raising=False)
    monkeypatch.setenv("INDICO_URL", CERN + "/")
    monkeypatch.setenv("INDICO_TOKEN", "indp_x")
    assert Settings.from_env().instances == (Instance("indico.cern.ch", CERN, "indp_x"),)


@pytest.mark.parametrize("spec", ["cern", "cern=indico.cern.ch", "CERN LAB=https://x", f"a={CERN},a={HD}"])
def test_bad_instances_spec_is_refused(monkeypatch, spec):
    monkeypatch.setenv("INDICO_INSTANCES", spec)
    with pytest.raises(SystemExit, match="INDICO_INSTANCES"):
        Settings.from_env()


@respx.mock
async def test_event_times_are_given_in_the_event_timezone(settings):
    # the export API answers in the server's timezone (Europe/Zurich on indico.cern.ch)
    event = {
        "id": "8",
        "title": "Remote meeting",
        "timezone": "America/Sao_Paulo",
        "startDate": {"date": "2026-09-14", "time": "15:00:00", "tz": "Europe/Zurich"},
        "endDate": {"date": "2026-09-14", "time": "16:00:00", "tz": "Europe/Zurich"},
        "contributions": [{"startDate": {"date": "2026-09-14", "time": "15:30:00", "tz": "Europe/Zurich"}}],
    }
    respx.get(BASE + "/export/event/8.json").respond(json={"results": [event]})
    respx.get(BASE + "/export/categ/3.json").respond(json={"results": [event]})

    _, listed = await call(settings, "indico_list_category_events", category_id=3)
    _, detail = await call(settings, "indico_get_event", event_id=8)

    assert listed["events"][0]["start"] == "2026-09-14T10:00:00"
    assert detail["startDate"] == {"date": "2026-09-14", "time": "10:00:00", "tz": "America/Sao_Paulo"}
    assert detail["contributions"][0]["startDate"]["time"] == "10:30:00"


@respx.mock
async def test_search_results_say_which_timezone_they_use(settings):
    found = {"id": 1291157, "title": "ICHEP 2024", "startDate": {"date": "2024-07-17", "time": "06:00:00", "tz": "UTC"}}
    respx.get(BASE + "/export/event/search/ICHEP%202024.json").respond(json={"results": [found]})
    _, result = await call(settings, "indico_search_events", query="ICHEP 2024")
    assert result["events"][0] == {
        "id": 1291157,
        "title": "ICHEP 2024",
        "start": "2024-07-17T06:00:00",
        "timezone": "UTC",
    }
