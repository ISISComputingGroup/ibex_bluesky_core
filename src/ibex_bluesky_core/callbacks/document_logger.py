"""Logs all documents that the BlueSky run engine creates via a callback"""

import os, json
from pathlib import Path

DEFAULT_LOG_LOCATION = Path(os.path.join("C:\\","instrument","var","logs","bluesky","raw_documents"))


class DocLoggingCallback():

    def __init__(self) -> None:
        self.current_start_document = None
        self.filename = None

    def __call__(self, name, document):

        if name == "start":

            DEFAULT_LOG_LOCATION.mkdir(parents=True, exist_ok=True)

            self.current_start_document = document["uid"]
            self.filename = os.path.join(DEFAULT_LOG_LOCATION, f"{self.current_start_document}.log")

        assert self.current_start_document is not None, "Saw a non-start document before a start."
        
        to_write = {
            "type": name,
            "document": document
        }

        with open(self.filename, 'a') as outfile:
            outfile.write(f"{json.dumps(to_write)}\n")

        return 0
