# Environmental footprint

## How it works

### Model impact

For each customer model, we define the number of total and active parameters, as well as the zone, in the `config.yml` file. Example:

```yaml
models:
  - id: language-model
    type: text-generation
    clients:
      - model: openai/gpt-4o-mini
        type: openai
        params:
            total: 35
            active: 35
            zone: WOR
```

Environmental impact is calculated using the Ecologits library. EcoLogits aims to give a comprehensive view of the environmental footprint of generative AI models at inference. 


For each call to the generative AI model, in addition to the model response, we return the following impacts: 
  - Energy: related to the final electricity consumption in kWh.
  - Global Warming Potential (GWP): related to climate change, commonly known as GHG emissions in kgCO2eq.
