import logging
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes

logger = logging.getLogger(__name__)

def impact_carbon(
    active_params: int,
    total_params: int,
    model_zone: str,
    token_count: int,
    request_latency: float
) -> dict:
    """Calculate carbon impact of a model inference using direct parameters.

    Args:
        active_params: Number of active parameters (in millions or billions, must match compute_llm_impacts expectations)
        total_params: Total number of parameters (in millions or billions, must match compute_llm_impacts expectations)
        model_zone: Electricity mix zone (e.g., "FR", "EU", "US")
        token_count: Number of output tokens
        request_latency: Latency of the inference (in seconds)

    Returns:
        dict: Dictionary of computed impacts
    """
    if not isinstance(token_count, (int, float)) or token_count < 0:
        raise ValueError("token_count must be a positive number")
    if not isinstance(request_latency, (int, float)) or request_latency < 0:
        raise ValueError("request_latency must be a positive number")
    if not isinstance(model_zone, str):
        raise ValueError("model_zone must be a string")

    electricity_mix = electricity_mixes.find_electricity_mix(zone=model_zone)
    if not electricity_mix:
        raise ValueError(f"electricity zone {model_zone} not found")

    impacts = compute_llm_impacts(
        model_active_parameter_count=active_params,
        model_total_parameter_count=total_params,
        output_token_count=token_count,
        if_electricity_mix_adpe=electricity_mix.adpe,
        if_electricity_mix_pe=electricity_mix.pe,
        if_electricity_mix_gwp=electricity_mix.gwp,
        request_latency=request_latency,
    )

    return impacts.model_dump()
