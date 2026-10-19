"""Optional context-local ceilings; normal interactive authorization stays unchanged."""

from contextlib import contextmanager
from contextvars import ContextVar

current = ContextVar("deelvo_authorization_ceiling", default=None)


@contextmanager
def limited(ceiling):
    marker = current.set(ceiling)
    try:
        yield
    finally:
        current.reset(marker)


def permits(actor, action, scope):
    ceiling = current.get()
    return (
        ceiling is None
        or ceiling.owner_id != actor.pk
        or (action in ceiling.actions and ceiling.includes(scope))
    )
