from dataclasses import replace

from hepflow.utils import write_json

from fasthep_render.model import RenderAttempt, RenderOutcome


def write_render_attempt(
    *,
    attempt: RenderAttempt,
    outcome: RenderOutcome,
    status_path: str,
) -> None:
    final = replace(
        attempt,
        status=outcome.status,
        message=outcome.message,
        meta=outcome.meta or {},
    )
    write_json(final.to_dict(), status_path)
