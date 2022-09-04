Jupyter-Jsonnet
===============

This package provides a Jupyter Kernel to support the Jsonnet language.  It is
based on the official Jsonnet Python bindings.

After installing it, you need to register it to Jupyter with the command:
```sh
python3 -m jupyter_jsonnet.post_install
```

This kernel extends jsonnet syntax slightly to permit

* Cells containing only statements (These produce no result, but are checked
  for errrors).
* Definitions (statements) from previous cells to carry over, even if the cell
  containing the definition produced a result.
* Using `//jupyter: string` as the first line of a cell causes the output to be
  the raw string instead of the json-escaped version, similarly to `--string`
  at the CLI.  For use with e.g. `std.manifestTomlEx()`

The parsing to separate statements from expressions is very simple, and can
easily be fooled by semicolons that do not terminate statements, like in
comments or strings.

Building from Source
====================
Ensure PyPA `build` is installed:

```sh
pip3 install build
python3 -m build
```

I don't currently have a satisfactory way of doing develop/editable installs.
