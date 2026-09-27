# Attach slides and links

Material can hang on an event, a session or a contribution.

## Attach a link

Ask the agent, for example:

> Attach the recording https://cds.cern.ch/record/123 to the "Data quality" talk of event 1740001, titled "Recording".

It calls `indico_add_link` with `contribution_id`. Pass `session_id` for a session, or neither for the event itself.

## Upload a file

Uploads are off until you name a folder the server may read from:

```console
-e INDICO_UPLOAD_DIR=~/talks/to-upload
```

Copy the slides into that folder, then:

> Upload slides.pdf to the "Data quality" talk.

The agent calls `indico_upload_file` with `file_path="slides.pdf"`. Relative paths are read inside the upload folder; paths leading outside it are refused.

## Find what is attached

`indico_get_event` returns the material of the event and, with `detail="contributions"`, of each contribution.
