# Dev note

## Tools that we use

- [Poetry](https://python-poetry.org/): package and dependency management
- [bytewax](https://bytewax.io/): stream processing in python
- [Ruff](https://docs.astral.sh/ruff/): linter and formater
- [Pre-commit](https://pre-commit.com/): add hooks that will run before you commit
- [mypy](https://mypy-lang.org/): static type check
- [mkdocs-material](https://squidfunk.github.io/mkdocs-material/): documentation webpage

## Standards

Follows guide at [scientific-python](https://learn.scientific-python.org/development/)

## Serialization

- model_dump doesn't convert enum to its value. However, by using IntEnum or StrEnum, the enum can be serialized

## PEP

- PEP 585: use list, dict instead of List, Dict
- PEP 604: use X | Y insated of Union\[X,Y\]

## K8s models

k8s python client has model auto generated from the openapi spec but is not in pydantic
