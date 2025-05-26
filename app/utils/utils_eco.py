import logging
from pathlib import Path
import toml
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes

logger = logging.getLogger(__name__)


DEFAULT_PARAMS = {"params": 100, "active_params": 100, "total_params": 100}


def load_models_info() -> dict:
    config_path = Path("app/utils/models-extra-info.toml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = toml.load(f)
    return config


def get_model_name_from_path(full_name: str) -> str:
    return full_name.split("/")[-1].lower()


def estimate_model_params(model_name: str) -> dict:
    """Estimate model parameters based on its name and known patterns."""
    name_lower = model_name.lower()

    # Size estimation patterns
    size_patterns = {"mini": 3, "small": 7, "medium": 35, "large": 70, "xl": 200, "xxl": 400}

    # Mixture of Experts patterns
    moe_patterns = ["moe", "mixture", "sparse"]

    # Total parameters estimation
    total_params = DEFAULT_PARAMS["total_params"]
    for pattern, size in size_patterns.items():
        if pattern in name_lower:
            total_params = size
            break

    # Active parameters estimation
    active_params = total_params
    if any(pattern in name_lower for pattern in moe_patterns):
        active_params = total_params // 4  # MoE models typically use 1/4 of total parameters

    return {
        "params": total_params,
        "total_params": total_params,
        "active_params": active_params,
        "estimated": True,
    }


def build_model_extra_info(model_name: str, models_info_params: dict) -> dict:
    """Build model information dictionary with default values for missing parameters."""
    std_name = get_model_name_from_path(model_name)
    logger.debug(f"Processing model: {std_name}")

    # Case-insensitive search in TOML keys
    model = None
    for key in models_info_params.keys():
        if key.lower() == std_name:
            model = models_info_params[key]
            break

    if model is None:
        logger.debug(f"Model {std_name} not found in models-extra-info.toml. Estimating parameters...")
        model = estimate_model_params(std_name)
        model["id"] = std_name.lower()
    else:
        model = model.copy()
        model["id"] = model.get("id", std_name).lower()
        model["estimated"] = False

    # Handle size parameters
    if not any(model.get(key) for key in ("friendly_size", "params", "total_params")):
        model["params"] = DEFAULT_PARAMS["params"]

    # Map friendly sizes to parameter counts
    PARAMS_SIZE_MAP = {"XS": 3, "S": 7, "M": 35, "L": 70, "XL": 200}
    model["params"] = model.get(
        "total_params", PARAMS_SIZE_MAP.get(model.get("friendly_size"), DEFAULT_PARAMS["params"])
    )

    # if quantization, divide by 2
    if model.get("quantization") == "q8":
        model["active_params"] = model.get("active_params", model["params"]) // 2
        model["total_params"] = model.get("total_params", model["params"]) // 2
    else:
        model["active_params"] = model.get("active_params", model["params"])
        model["total_params"] = model.get("total_params", model["params"])

    # Calculate required RAM based on quantization
    if model.get("quantization") == "q8":
        model["required_ram"] = model["params"] * 2  # q8 quantization uses 2 bytes per parameter
    else:
        model["required_ram"] = model["params"]  # Default: 1 byte per parameter

    logger.debug(f"Model info: {model}")
    return model


def impact_carbon(model_name: str, model_zone: str, token_count: int, request_latency: float) -> dict:
    """Calculate carbon impact of a model inference."""
    logger.debug(f"model_name : {model_name}")
    logger.debug(f"model_zone : {model_zone}")
    logger.debug(f"token_count : {token_count}")

    models_info = load_models_info()
    model_data = build_model_extra_info(model_name, models_info)

    # Validate input parameters
    if not isinstance(token_count, (int, float)) or token_count < 0:
        raise ValueError("token_count must be a positive number")
    if not isinstance(request_latency, (int, float)) or request_latency < 0:
        raise ValueError("request_latency must be a positive number")

    # Get model parameters, always using DEFAULT_PARAMS as fallback
    mapc = model_data.get("active_params", model_data.get("params", DEFAULT_PARAMS["active_params"]))
    matpc = model_data.get("total_params", model_data.get("params", DEFAULT_PARAMS["total_params"]))

    # Determine electricity mix zone
    if not isinstance(model_zone, str):
        raise ValueError("model_zone must be a string")

    # Use French electricity mix for Albert models, world average for others
    electricity_mix_zone = model_zone
    electricity_mix = electricity_mixes.find_electricity_mix(zone=electricity_mix_zone)

    if not electricity_mix:
        raise ValueError(f"electricity zone {electricity_mix_zone} not found")

    # Calculate carbon impact using Ecologits
    impacts = compute_llm_impacts(
        model_active_parameter_count=mapc,
        model_total_parameter_count=matpc,
        output_token_count=token_count,
        if_electricity_mix_adpe=electricity_mix.adpe,
        if_electricity_mix_pe=electricity_mix.pe,
        if_electricity_mix_gwp=electricity_mix.gwp,
        request_latency=request_latency,
    )

    # Convert to dict and add estimation flag
    impacts_dict = impacts.model_dump()
    impacts_dict["estimated"] = model_data.get("estimated", False)

    return impacts_dict
