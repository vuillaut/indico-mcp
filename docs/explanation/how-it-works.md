# How the server talks to Indico

An MCP server is a translator. The agent calls a tool such as `indico_get_timetable(event_id=1291157)`; the server turns that into HTTP requests to Indico and returns a cleaned-up JSON result. The agent never sees Indico's HTML or its raw export format.

## Reads use documented APIs

Indico has two read APIs that it documents and keeps stable:

- the **HTTP export API** under `/export/`, which returns events, categories and timetables as JSON;
- the **check-in API** under `/api/checkin/`, used by Indico's check-in app, which returns registration forms and registrants.

Every read tool except one uses these. The exception is `indico_list_contributions`, which reads the JSON behind the contribution management page. It returns every contribution of the event with its database id, session, schedule and people, and it needs the **Everything** token scope and management rights on the event.

## Writes go through the web forms

Indico has no public API for creating or editing events. Its management pages are the only way in. The server does what your browser does: it requests the same dialogs and endpoints, with your personal token instead of a login cookie. Indico allows this for tokens with the **Everything (all methods)** scope.

There are two kinds of write endpoints.

**JSON endpoints.** Scheduling, moving and unscheduling timetable entries, assigning a talk to a session, and deletes all use small JSON endpoints. The server sends a few fields and reads a JSON answer.

**HTML forms.** Creating and editing events, sessions, talks and attachments go through WTForms dialogs. Here the server:

1. loads the form as HTML;
2. reads every field and its current value, the way a browser would;
3. changes only the fields you asked for;
4. submits the whole form.

Step 4 matters. A form submission that leaves out a field doesn't mean "keep it". To Indico, a missing checkbox means unchecked and a missing person list means no speakers. Posting only the changed fields would wipe data. Loading the form first costs one extra request per edit and prevents that.

If you ask to change a field the form doesn't have, the server refuses before submitting anything and lists the fields the form does have. This is the usual symptom of an Indico upgrade that renamed a field. The server stops rather than guess.

When Indico rejects a submission, it sends the form back with error messages attached to fields. The server extracts them and returns `Indico rejected the form: title: This field is required`, so the agent can fix its input.

## Why writes are fragile

The internal endpoints are not a contract. The Indico developers change them when they change the web pages, and a minor Indico release can rename a form field or move a URL. Reads through the export API are safe from this; writes are not.

The write tools were written from Indico 3.3's source code and tested against recorded responses. Other 3.x versions share most of the code, but that is no guarantee. [Indico endpoints](../reference/endpoints.md) lists what each tool calls, so you can compare with your server after an upgrade.

## One HTTP client per instance

With several instances configured, the server opens one HTTP connection pool per Indico server. A call resolves its `instance` argument to one of them, picks that instance's token, and sends the request there. A token is never attached to a request for another host.
