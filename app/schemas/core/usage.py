from enum import Enum

import pycountry

CountryCodes = [country.alpha_3 for country in pycountry.countries]
CountryCodes.append("WOR")  # Add world as a country code
CountryCodes = {str(lang).upper(): str(lang) for lang in sorted(set(CountryCodes))}
CountryCodes = Enum("CountryCodes", CountryCodes, type=str)
