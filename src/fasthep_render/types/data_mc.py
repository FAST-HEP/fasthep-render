from dataclasses import dataclass, field
from typing import Any, Literal

from hepflow.model.issues import FlowIssue, IssueLevel
from hepflow.model.render_types import RenderCommonSpec, RenderTypeSpec

from fasthep_render.types.common import resolve_single_hist_input


@dataclass(frozen=True)
class DataMcParams:
    data: str = "data"
    backgrounds: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    include_signals_in_stack: bool = True
    show_mc_uncertainty: bool = True
    stack: bool = True
    stack_order: Literal["legend", "reverse_legend"] = "reverse_legend"
    ratio: bool = True

    histtype_mc: Literal["fill", "step", "bar"] = "fill"
    histtype_signal: Literal["step", "fill", "bar"] = "step"

    legend_auto_ncol_threshold: int = 5
    legend_max_ncol: int = 4

    ratio_ylim: tuple[float, float] = (0.5, 1.5)
    ratio_ylabel: str = "Data/MC"


def parse_data_mc_params(spec_dict: dict[str, Any]) -> DataMcParams:
    return DataMcParams(**dict(spec_dict.get("data_mc") or {}))


def validate_data_mc_params(
    common: RenderCommonSpec,
    params: DataMcParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    issues: list[FlowIssue] = []

    available = set(context.get("available_datasets") or [])
    needed = [params.data, *list(params.backgrounds), *list(params.signals)]
    missing = sorted(x for x in needed if x not in available)

    if missing:
        issues.append(
            FlowIssue(
                level=IssueLevel.ERROR,
                code="RENDER_SPEC_MISSING_DATASETS",
                message="data_mc renderer references datasets not available after transforms",
                meta={"missing": missing, "available": sorted(available)},
            )
        )
    return issues


DATA_MC_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_data_mc_params,
    validate=validate_data_mc_params,
    resolve_input=resolve_single_hist_input,
)
