from typing import Any

import hist
from hepflow.model.render_types import RenderCommonSpec

from fasthep_render.common import find_dataset_axis_name


def make_group_map_from_transform(
    by: str | dict[str, list[str]],
    *,
    dataset_meta_by_name: dict[str, dict[str, Any]],
    dataset_names: list[str],
) -> dict[str, str]:
    """
    Returns sample_name -> group_name
    """
    if isinstance(by, str):
        if by != "dataset_group":
            msg = f"Unsupported group transform mode: {by!r}"
            raise ValueError(msg)

        out: dict[str, str] = {}
        for ds in dataset_names:
            meta = dataset_meta_by_name.get(ds) or {}
            out[ds] = str(meta.get("group") or ds)
        return out

    if isinstance(by, dict):
        group_map: dict[str, str] = {}
        for group_name, members in by.items():
            for ds in members:
                group_map[str(ds)] = str(group_name)

        # samples not listed stay in their own group
        for ds in dataset_names:
            group_map.setdefault(ds, ds)
        return group_map

    msg = f"Invalid group transform 'by': {by!r}"
    raise ValueError(msg)


def apply_group_transform(
    h,
    group_map: dict[str, str],
    dataset_axis_name: str = "dataset",
):
    """
    Returns dict[group_name, hist] for now.
    This is the easiest minimal implementation for renderers.
    """
    grouped: dict[str, Any] = {}

    ax = h.axes[dataset_axis_name]
    dataset_names = [ax.value(i) for i in range(ax.size)]

    for ds in dataset_names:
        group = group_map.get(ds, ds)
        h_ds = h[{dataset_axis_name: ds}]

        if group in grouped:
            grouped[group] = grouped[group] + h_ds
        else:
            grouped[group] = h_ds

    return grouped


def rebuild_hist_from_grouped_samples(
    h,
    *,
    dataset_axis_name: str,
    grouped: dict[str, Any],
):
    """
    Rebuild a histogram with the dataset axis replaced by grouped categories.

    Parameters
    ----------
    h:
        Original histogram with dataset axis.
    dataset_axis_name:
        Name of the dataset axis to replace.
    grouped:
        Mapping group_name -> histogram slice without dataset axis.
    """
    axis_names = [ax.name for ax in h.axes]
    ds_axis_idx = axis_names.index(dataset_axis_name)

    # Build new axes: replace dataset axis with grouped categories
    new_axes = []
    for i, ax in enumerate(h.axes):
        if i == ds_axis_idx:
            new_axes.append(
                hist.axis.StrCategory(
                    list(grouped.keys()),
                    name=ax.name,
                    label=getattr(ax, "label", ax.name),
                )
            )
        else:
            new_axes.append(ax)

    out = hist.Hist(*new_axes, storage=h.storage_type())

    view = out.view(flow=False)

    for i, (_group_name, h_group) in enumerate(grouped.items()):
        slicer: list[Any] = [slice(None)] * view.ndim
        slicer[ds_axis_idx] = i
        index = tuple(slicer)

        gview = h_group.view(flow=False)

        if hasattr(view, "value") and hasattr(view, "variance"):
            view.value[index] = gview.value
            view.variance[index] = gview.variance
        else:
            view[index] = gview

    return out


def apply_group_transform_to_products(
    *,
    products: dict[str, Any],
    transform,
    ctx: dict[str, Any],
) -> dict[str, Any]:
    h = products.get("hist")
    if h is None:
        return products

    dataset_axis_name = find_dataset_axis_name(h)
    if dataset_axis_name is None:
        return products

    ax = h.axes[dataset_axis_name]
    dataset_names = [ax.value(i) for i in range(ax.size)]

    datasets_cfg = ctx.get("datasets") or {}

    group_map = make_group_map_from_transform(
        transform.group.by,
        dataset_meta_by_name=datasets_cfg,
        dataset_names=dataset_names,
    )

    grouped: dict[str, Any] = {}
    for ds in dataset_names:
        group = group_map.get(ds, ds)
        h_ds = h[{dataset_axis_name: ds}]

        if group in grouped:
            grouped[group] = grouped[group] + h_ds
        else:
            grouped[group] = h_ds

    hist_grouped = rebuild_hist_from_grouped_samples(
        h,
        dataset_axis_name=dataset_axis_name,
        grouped=grouped,
    )
    return {
        **products,
        "before_grouping": h,
        "hist": hist_grouped,
        "groups": grouped,
        "group_map": group_map,
    }


def apply_render_transforms(
    *,
    products: dict[str, Any],
    common: RenderCommonSpec,
    render_params: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply ordered transforms from RenderSpec.

    Returns a new products-like dict for downstream renderers.
    """
    out = dict(products)

    for t in common.transforms or []:
        if t.kind == "group":
            out = apply_group_transform_to_products(
                products=out,
                transform=t,
                ctx=ctx,
            )
        elif t.kind == "scale":
            out = apply_scale_transform_to_products(
                products=out,
                transform=t,
                ctx=ctx,
            )
        else:
            msg = f"Unsupported transform kind: {t.kind}"
            raise ValueError(msg)

    return out


# def _scale_hist_scalar(h, factor: float):
#     return h * factor

# def _normalise_factors_dict(factors: dict[str, Any] | None) -> dict[str, float]:
#     out: dict[str, float] = {}
#     for k, v in (factors or {}).items():
#         if v is None:
#             continue
#         out[str(k)] = float(v)
#     return out


def normalize_factors(factors: dict[str, Any] | None) -> dict[str, float]:
    """
    Normalise user-provided scaling factors to a simple dict[str, float].
    """
    out: dict[str, float] = {}
    for k, v in (factors or {}).items():
        if v is None:
            continue
        out[str(k)] = float(v)
    return out


def make_sample_scale_map(
    *,
    dataset_names: list[str],
    by: str,
    factors: dict[str, float],
    dataset_meta_by_name: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """
    Build a sample-level scale map:
      dataset_name -> scale_factor

    Supports:
      by = "dataset_name"
      by = "dataset_group"
    """
    out: dict[str, float] = {}

    if by == "dataset_name":
        for ds in dataset_names:
            out[ds] = float(factors.get(ds, 1.0))
        return out

    if by == "dataset_group":
        for ds in dataset_names:
            meta = dataset_meta_by_name.get(ds) or {}
            group = str(meta.get("group") or ds)
            out[ds] = float(factors.get(group, 1.0))
        return out

    msg = f"Unsupported scale transform 'by': {by!r}"
    raise ValueError(msg)


def build_scaled_samples(
    h,
    *,
    dataset_axis_name: str,
    sample_scale_map: dict[str, float],
) -> dict[str, Any]:
    """
    Slice the histogram by dataset, scale each slice, and return:
      dataset_name -> scaled histogram slice
    """
    scaled_samples: dict[str, Any] = {}

    ax = h.axes[dataset_axis_name]
    dataset_names = [ax.value(i) for i in range(ax.size)]

    for ds in dataset_names:
        h_ds = h[{dataset_axis_name: ds}]
        sf = float(sample_scale_map.get(ds, 1.0))
        scaled_samples[ds] = h_ds * sf

    return scaled_samples


def rebuild_hist_from_scaled_samples(
    h,
    *,
    dataset_axis_name: str,
    sample_scale_map: dict[str, float],
):
    """
    Return a scaled copy of `h` while preserving the dataset axis.

    Works by scaling the histogram view directly along the dataset axis.
    """
    out = h.copy()

    axis_names = [ax.name for ax in out.axes]
    ds_axis_idx = axis_names.index(dataset_axis_name)

    view = out.view(flow=False)

    for ds, sf in sample_scale_map.items():
        idx = out.axes[dataset_axis_name].index(ds)

        slicer: list[Any] = [slice(None)] * view.ndim
        slicer[ds_axis_idx] = idx
        index = tuple(slicer)

        # Weight storage: values scale linearly, variances quadratically
        if hasattr(view, "value") and hasattr(view, "variance"):
            view.value[index] *= sf
            view.variance[index] *= sf * sf
        else:
            # Count / plain numeric storage
            view[index] *= sf

    return out


def apply_scale_transform_to_products(
    *,
    products: dict[str, Any],
    transform,
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """
    Apply scaling to products while preserving the dataset axis.

    Output contract:
      - before_scaling
      - hist
      - scaled_samples
      - scale_factors
    """
    scale = transform.scale
    if scale is None:
        return products

    if scale.mode != "overall":
        msg = (
            f"Unsupported scale transform mode for now: {scale.mode!r} "
            "(only 'overall' is implemented)"
        )
        raise ValueError(
            msg
        )

    if scale.factors_ref:
        msg = (
            "scale transform with factors_ref is not implemented yet "
            "(only inline factors are supported for now)"
        )
        raise ValueError(
            msg
        )

    h = products.get("hist")
    if h is None:
        return products

    dataset_axis_name = find_dataset_axis_name(h)
    if dataset_axis_name is None:
        return products

    ax = h.axes[dataset_axis_name]
    dataset_names = [ax.value(i) for i in range(ax.size)]

    dataset_meta_by_name = ctx.get("datasets") or {}

    factors = normalize_factors(scale.factors)

    sample_scale_map = make_sample_scale_map(
        dataset_names=dataset_names,
        by=scale.by,
        factors=factors,
        dataset_meta_by_name=dataset_meta_by_name,
    )

    scaled_samples = build_scaled_samples(
        h,
        dataset_axis_name=dataset_axis_name,
        sample_scale_map=sample_scale_map,
    )

    hist_scaled = rebuild_hist_from_scaled_samples(
        h,
        dataset_axis_name=dataset_axis_name,
        sample_scale_map=sample_scale_map,
    )

    return {
        **products,
        "before_scaling": h,
        "hist": hist_scaled,
        "scaled_samples": scaled_samples,
        "scale_factors": sample_scale_map,
    }
