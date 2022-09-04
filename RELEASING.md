# Releasing

    oaf commit
    python3 -m build
    oaf tag 0.2
    git push --tags

`python3 -m twine upload dist/*0.2*` (optionally `--repository testpypi`)

https://github.com/abentley/jupyter-jsonnet/releases/new

Remember to upload the wheel & source distribution

bump version number:

 * pyproject.toml
 * setup.py
 * kernel.py (implementation version number)
