# Document Logging Callback

The document logger is a callback that the BlueSky RunEngine subscribes to unconditionally. After receiving each document it will write documents in the same file with other documents sharing the same start document (In the same run). These logs are stored under `C://instrument/var/logs/bluesky/raw_documents` and are handled by the log rotation.

Each document is stored in a JSON format so can be both machine and human readable. It is in the format `{"type": name, "document": document}` whereby `name` is the type of the document, e.g start, stop, event, descriptor and the `document` is the document from BlueSky in JSON format. As these files are produced per BlueSky run, these will be useful for debugging.
