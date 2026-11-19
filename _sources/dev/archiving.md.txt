# Bluesky output archiving

:::{seealso}
{doc}`ADR 7 - bluesky output file archiving</architectural_decisions/007-output-file-archiving>`
:::

Bluesky writes output files initially to paths on the local data disk, which look like:

```
c:\data\RB123456\bluesky_scans\some_output_file.txt
```

Once bluesky has finished writing to the files, they will be marked as read-only.

These files are subsequently moved by an [archiving script](https://github.com/ISISComputingGroup/EPICS/blob/b22afd559d3cc86f33dedf1eda96f47110a3ad21/utils/move_bluesky_data_to_archive.py),
which is called regularly from a [scheduled task deployed via ansible](https://github.com/ISISComputingGroup/ansible-playbooks/blob/16612a01499f96d0761aad61de42e2e136c56163/windows/tasks/wincred.yaml#L155). This task runs every minute, and will move any bluesky outputs which are marked as read-only to
archive paths which look like:

```
\\isis.cclrc.ac.uk\inst$\NDX<inst>\Instrument\data\cycle_<cyclenum>\autoreduced\bluesky_scans\RB123456\some_output_file.txt
```

Once the files have been moved to the archive, they are deleted from the local instrument data area.

## Troubleshooting

### Files not being moved

- Check the archiving script has appropriate permissions for the archive by manually running
```
c:\instrument\apps\python3\python.exe c:\instrument\apps\epics\utils\move_bluesky_data_to_archive.py
```
- Check which files the script is picking up (it has a `--dry-run` flag to avoid actually moving data if needed)
- Verify that the files that are not being moved correctly have the read-only attribute set in Windows
