# File writing callbacks
## Human readable files

A callback (`HumanReadableOutputFileLoggingCallback`) exists to write all documents to a separate human-readable file which contains the specified fields. 

This callback will add units and honour precision for each field as well as add some metadata ie. the `uid` of each scan as well as the RB number, which is injected using the {doc}`/preprocessors/rbnumberpp`
