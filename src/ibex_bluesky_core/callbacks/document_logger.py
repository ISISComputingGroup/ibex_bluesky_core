"""Logs all documents that the BlueSky run engine creates via a callback."""

import json
from pathlib import Path
from typing import Any

log_location = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "raw_documents"


class DocLoggingCallback:
    """Logs all documents under log_location, with the file name of their UID (.log)."""

    def __init__(self) -> None:
        """Initialise current_start_document and filename."""
        self.current_start_document = None
        self.filename = None

    def __call__(self, name: str, document: dict[str, Any]) -> None:
        """Is called when a new document needs to be processed. Writes document to a file.

        Args:
            name: The type of the document e.g start, event, stop
            document: The contents of the docuement as a dictionary

        """
        if name == "start":
            log_location.mkdir(parents=True, exist_ok=True)

            self.current_start_document = document["uid"]
            self.filename = log_location / f"{self.current_start_document}.log"

        assert self.filename is not None, "Could not create filename."
        assert self.current_start_document is not None, "Saw a non-start document before a start."

        to_write: dict[str, Any] = {"type": name, "document": document}

        with open(self.filename, "a") as outfile:
            outfile.write(f"{json.dumps(to_write)}\n")
