# Document Logging Callback

The document logger is a callback that the BlueSky RunEngine subscribes to unconditionally. After receiving each document, if they share the same start document (in the same run) then it will write them to the same file. These logs are stored under `C:/instrument/var/logs/bluesky/raw_documents` and are handled by the log rotation.

Each document is stored in a JSON format so can be both machine and human readable. It is in the format `{"type": name, "document": document}` whereby `name` is the type of the document, e.g start, stop, event, descriptor and the `document` is the [document from BlueSky in JSON format](https://blueskyproject.io/bluesky/main/documents.html). As these files are produced per BlueSky run, these will be useful for debugging.
