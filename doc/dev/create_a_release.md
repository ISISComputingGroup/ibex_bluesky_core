# Release Process

Releases are created automatically via a github action. 

To create a release just create a new git tag on the commit on main:
```
git pull
git checkout main
git tag <release.version.number>
git push origin tag <release.version.number>
```

This will start a workflow that will check that all linters and tests pass, 
and then publish a new release with the version number specified in the tag to 
[Pypi](https://pypi.org/project/ibex-bluesky-core/0.0.1/) and github. The new 
release can then be installed via `pip install ibex_bluesky_core`. 

The workflow must be approved by someone in the ICP-Write group. To do this go 
to the action (Actions -> the action on the tag) and approve it.

Credentials for Pypi can be found on keeper.
