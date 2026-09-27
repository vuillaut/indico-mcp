from indico_mcp.forms import parse_form

FORM = """
<form>
  <input type="hidden" name="title" value="Old title">
  <input type="hidden" name="person_link_data" value="[{&quot;last_name&quot;: &quot;Curie&quot;}]">
  <textarea name="description">Keep me</textarea>
  <input type="hidden" name="start_dt" value="2026-10-05">
  <input type="hidden" name="start_dt" value="09:00">
  <input type="checkbox" name="update_timetable" value="y" checked>
  <input type="checkbox" name="protected" value="y">
  <input type="radio" name="mode" value="public">
  <input type="radio" name="mode" value="inheriting" checked>
  <select name="type"><option value="">none</option><option value="3" selected>Talk</option></select>
  <input type="text" name="locked" value="x" disabled>
  <input type="submit" name="ok" value="Save">
  <input id="unnamed-widget-input" value="ignored">
</form>
"""


def test_parse_keeps_what_a_browser_submits():
    form = parse_form(FORM)
    assert form.fields == [
        ("title", "Old title"),
        ("person_link_data", '[{"last_name": "Curie"}]'),
        ("description", "Keep me"),
        ("start_dt", "2026-10-05"),
        ("start_dt", "09:00"),
        ("update_timetable", "y"),
        ("mode", "inheriting"),
        ("type", "3"),
    ]
    # unchecked boxes are known even though they submit nothing
    assert {"protected", "mode"} <= form.known
    assert "locked" not in form.known and "ok" not in form.known


def test_merge_only_touches_overrides():
    merged = parse_form(FORM).merged({"title": "New", "start_dt": ["2026-11-01", "10:30"], "protected": "y"})
    assert merged == [
        ("title", "New"),
        ("person_link_data", '[{"last_name": "Curie"}]'),
        ("description", "Keep me"),
        ("start_dt", "2026-11-01"),
        ("start_dt", "10:30"),
        ("update_timetable", "y"),
        ("mode", "inheriting"),
        ("type", "3"),
        ("protected", "y"),
    ]


def test_validation_errors_are_extracted():
    html = """
    <form><div class="form-group" data-error="&lt;ul&gt;&lt;li&gt;This field is required.&lt;/li&gt;&lt;/ul&gt;">
      <input name="title" value="">
    </div></form>
    """
    assert parse_form(html).errors == {"title": "This field is required."}


def test_select_without_selection_submits_first_option():
    form = parse_form('<select name="tz"><option value="UTC">UTC</option><option>Europe/Paris</option></select>')
    assert form.fields == [("tz", "UTC")]
