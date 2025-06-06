import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.helpers.agents import AgentsManager
from app.schemas.core.usage import CountryCodes
from app.schemas.usage import CarbonFootprintUsage, CarbonFootprintUsageKWh, CarbonFootprintUsageKgCO2eq
from app.utils.carbon import get_carbon_footprint

class TestGetCarbonFootprint:
    def test_get_carbon_footprint_return_null_footprint_when_model_params_not_define(self):
        #Given 
        active_params = 0
        total_params = None
        model_zone = CountryCodes.WOR
        token_count = 1
        request_latency = 0.01
        expected_carbon_footprint = CarbonFootprintUsage(kWh=CarbonFootprintUsageKWh(min=0.0, max=0.0), kgCO2eq=CarbonFootprintUsageKgCO2eq(min=0.0, max=0.0))
        #When
        result= get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)
        #Then
        assert expected_carbon_footprint == result

    def test_get_carbon_footprint_return_null_footprint_when_token_count_is_null(self):
        #Given 
        active_params = 0
        total_params = 0
        model_zone = CountryCodes.WOR
        token_count = 0
        request_latency = 0.01
        expected_carbon_footprint = CarbonFootprintUsage(kWh=CarbonFootprintUsageKWh(min=0.0, max=0.0), kgCO2eq=CarbonFootprintUsageKgCO2eq(min=0.0, max=0.0))
        #When
        result= get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)
        #Then
        assert expected_carbon_footprint == result

    def test_get_carbon_footprint_return_error_when_token_count_is_negative(self):
        #Given 
        active_params = 0
        total_params = 0
        model_zone = CountryCodes.WOR
        token_count = -10
        request_latency = 0.01
        expected_carbon_footprint = ValueError("token_count must be a positive number")
        #When-Then
        with pytest.raises(ValueError):
            get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)

# TODO: AUDREY faire les 3 tests d'erreur

    def test_get_carbon_footprint_return_footprint(self):
        #Given 
        active_params = 1
        total_params = 1
        model_zone = CountryCodes.WOR
        token_count = 1
        request_latency = 0.01
        expected_carbon_footprint = CarbonFootprintUsage(kWh=CarbonFootprintUsageKWh(min=0.0, max=0.0), kgCO2eq=CarbonFootprintUsageKgCO2eq(min=0.0, max=0.0))
        #When
        result= get_carbon_footprint(active_params, total_params, model_zone, token_count, request_latency)
        #Then
        assert expected_carbon_footprint == result