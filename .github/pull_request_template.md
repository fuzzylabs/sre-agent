_Write a short description which explains what this pull request does and, briefly, how._

### What

### Why

### How

### Extra

_If new dependencies are introduced to the project, please list them here:_

* _new dependency_

## Checklist

Please ensure you have done the following:

* [ ] I have run application tests ensuring nothing has broken.
* [ ] I have updated the documentation if required.
* [ ] I have added tests which cover my changes.

## Type of change

Make sure to update label on right hand panel.

## MacOS tests

To trigger the CI to run on a macOS backed workflow, add the `macos-ci-test` label to the pull request (PR).

Our advice is to only run this workflow when testing the compatability between operating systems for a change that you've made, e.g., adding a new dependency to the virtual environment.

> Note: This can take up to 5 minutes to run. This workflow costs x10 more than a Linux-based workflow, use at discretion.
