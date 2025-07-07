from types import SimpleNamespace

import pytest

from app.schemas.core.usage import CountryCodes
from app.schemas.usage import CarbonFootprintUsage, CarbonFootprintUsageKWh, CarbonFootprintUsageKgCO2eq
from app.utils.carbon import get_carbon_footprint


def dict_to_namespace(d):
    if isinstance(d, dict):
        namespace_dict = {k: dict_to_namespace(v) for k, v in d.items()}
        return SimpleNamespace(**namespace_dict)
    elif isinstance(d, list):
        return [dict_to_namespace(item) for item in d]
    else:
        return d


class TestGetCarbonFootprint:
    def test_get_carbon_footprint_return_null_footprint_when_model_params_not_define(self):
        # Given
        active_params = 0
        total_params = None
        model_zone = CountryCodes.WOR
        token_count = 1
        request_latency = 0.01
        expected_carbon_footprint = CarbonFootprintUsage(
            kWh=CarbonFootprintUsageKWh(min=0.0, max=0.0), kgCO2eq=CarbonFootprintUsageKgCO2eq(min=0.0, max=0.0)
        )
        # When
        result = get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)
        # Then
        assert expected_carbon_footprint == result

    def test_get_carbon_footprint_return_null_footprint_when_token_count_is_null(self):
        # Given
        active_params = 0
        total_params = 0
        model_zone = CountryCodes.WOR
        token_count = 0
        request_latency = 0.01
        expected_carbon_footprint = CarbonFootprintUsage(
            kWh=CarbonFootprintUsageKWh(min=0.0, max=0.0), kgCO2eq=CarbonFootprintUsageKgCO2eq(min=0.0, max=0.0)
        )
        # When
        result = get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)
        # Then
        assert expected_carbon_footprint == result

    def test_get_carbon_footprint_return_error_when_token_count_is_not_int_or_float(self):
        # Given
        active_params = 0
        total_params = 0
        model_zone = CountryCodes.WOR
        token_count = "10"
        request_latency = 0.01
        # When-Then
        with pytest.raises(ValueError, match="token_count must be a positive number"):
            get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)

    def test_get_carbon_footprint_return_error_when_token_count_is_negative(self):
        # Given
        active_params = 0
        total_params = 0
        model_zone = CountryCodes.WOR
        token_count = -10
        request_latency = 0.01
        # When-Then
        with pytest.raises(ValueError, match="token_count must be a positive number"):
            get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)

    def test_get_carbon_footprint_return_error_when_request_latency_is_not_int_or_float(self):
        # Given
        active_params = 0
        total_params = 0
        model_zone = CountryCodes.WOR
        token_count = 10
        request_latency = "0.01"
        # When-Then
        with pytest.raises(ValueError, match="request_latency must be a positive number"):
            get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)

    def test_get_carbon_footprint_return_error_when_request_latency_is_negative(self):
        # Given
        active_params = 0
        total_params = 0
        model_zone = CountryCodes.WOR
        token_count = 10
        request_latency = -0.01
        # When-Then
        with pytest.raises(ValueError, match="request_latency must be a positive number"):
            get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)

    def test_get_carbon_footprint_return_footprint(self, mocker):
        # Given
        mocked_electricity_mix = mocker.patch("app.utils.carbon.electricity_mixes.find_electricity_mix")
        mocked_electricity_mix.return_value = SimpleNamespace(adpe=1, pe=2, gwp=3)
        mocked_compute_llm_impacts = mocker.patch("app.utils.carbon.compute_llm_impacts")
        mocked_compute_llm_impacts.return_value = dict_to_namespace(
            {"energy": {"value": {"min": 1, "max": 2}}, "gwp": {"value": {"min": 0, "max": 3}}}
        )
        active_params = 1
        total_params = 1
        model_zone = CountryCodes.WOR
        token_count = 1
        request_latency = 0.01
        expected_carbon_footprint = CarbonFootprintUsage(
            kWh=CarbonFootprintUsageKWh(min=1.0, max=2.0), kgCO2eq=CarbonFootprintUsageKgCO2eq(min=0.0, max=3.0)
        )
        expected_compute_llm_impacts_args = {
            "if_electricity_mix_adpe": 1,
            "if_electricity_mix_pe": 2,
            "if_electricity_mix_gwp": 3,
            "model_active_parameter_count": 1,
            "model_total_parameter_count": 1,
            "output_token_count": 1,
            "request_latency": 0.01,
        }
        # When
        result = get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)
        # Then
        assert expected_carbon_footprint == result
        assert mocked_compute_llm_impacts.call_args_list[0][1] == expected_compute_llm_impacts_args
