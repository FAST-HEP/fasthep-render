"""Experimental FAST-HEP render prototypes.

Nothing here is public API: no stability promise, not exported from
``fasthep_render``, not in the docs, not in the changelog.
"""

import warnings


class ExperimentalWarning(UserWarning):
    """Raised on import of code that is an exploratory prototype."""


warnings.warn(
    "fasthep_render.experimental is an exploratory prototype without any "
    "stability guarantee.",
    ExperimentalWarning,
    stacklevel=2,
)
