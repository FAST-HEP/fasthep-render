from typing import Any

from fasthep_render.render_types import RenderCommonSpec


def resolve_single_hist_input(
    common: RenderCommonSpec,
    params: Any,
    context: dict[str, Any],
) -> dict[str, Any]:
    explicit_inputs = dict(context.get("explicit_inputs") or {})
    default_product = context.get("default_product")

    if explicit_inputs:
        if len(explicit_inputs) == 1:
            _, only_product = next(iter(explicit_inputs.items()))
            return {
                "product": only_product,
                "level": "global",
                "path": f"{only_product}.pkl",
            }
        return {
            "products": explicit_inputs,
        }

    if not default_product:
        msg = "No default product available for renderer input resolution"
        raise ValueError(msg)

    return {
        "product": str(default_product),
        "level": "global",
        "path": f"{default_product}.pkl",
    }
