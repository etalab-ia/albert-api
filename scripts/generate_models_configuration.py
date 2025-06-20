#!/usr/bin/env python3
import os
import yaml

MODEL_TYPES = {
    "text-embeddings-inference": "Text Embeddings",
    "text-classification": "Classification de Texte",
    "automatic-speech-recognition": "Reconnaissance Vocale",
    "text-generation": "Génération de Texte",
}


DEFAULT_URLS = {"openai": "https://api.openai.com", "albert": "https://albert.api.etalab.gouv.fr"}


def main():
    print("\n" + "=" * 60)
    print("MODELS CONFIGURATION FOR ALBERT-API")
    print("=" * 60)
    configuration_file_path = ask_configuration_file_path()
    models_configuration = ask_models_configuration()
    existing_config = get_existing_configuration(configuration_file_path)
    write_models_configuration(configuration_file_path, existing_config, models_configuration)
    display_configuration_summary(models_configuration)


def ask_configuration_file_path():
    configuration_file_path = input("Where do you want to store the configuration file ? [config.yml]: ").strip()
    if not configuration_file_path:
        configuration_file_path = "config.yml"
    return configuration_file_path


def ask_models_configuration():
    models = []
    for model_type, display_name in MODEL_TYPES.items():
        question = f"Do want to add a {display_name} ({model_type}) model ?"

        if ask_yes_no(question):
            while True:
                try:
                    count = input(f"How many {display_name} models do you want ? [1]: ").strip()
                    if not count:
                        count = 1
                    else:
                        count = int(count)

                    if count < 1:
                        print_error("The number of models should be at least 1")
                        continue
                    break
                except ValueError:
                    print_error("Invalid number")

            for i in range(count):
                suffix = f" #{i + 1}" if count > 1 else ""
                model_config = get_model_config(model_type, f"{display_name}{suffix}")
                models.append(model_config)
    return models


def get_existing_configuration(configuration_file_path: str):
    existing_config = {}
    if os.path.exists(configuration_file_path):
        try:
            with open(configuration_file_path, "r", encoding="utf-8") as f:
                existing_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print_error(f"Error when opening configuration file {configuration_file_path}: {e}")
            existing_config = {}
    return existing_config


def write_models_configuration(configuration_file_path, existing_config, models_configuration):
    existing_config["models"] = models_configuration
    with open(configuration_file_path, "w", encoding="utf-8") as f:
        yaml.dump(existing_config, f, default_flow_style=False, indent=2, allow_unicode=True, sort_keys=False)


def display_configuration_summary(models_configuration):
    print(f"\n✅ Configuration saved with {len(models_configuration)} model(s)")
    if models_configuration:
        print("\n" + "=" * 40)
        print("CONFIGURATION SUMMARY")
        print("=" * 40)
        for model in models_configuration:
            for client in model["clients"]:
                print(f"  - {model['id']} ({model['type']}) - {client['model']}")


def ask_yes_no(question):
    while True:
        response = input(f"{question} (y/n): ").lower().strip()
        if response in ["y", "yes", "o", "oui"]:
            return True
        elif response in ["n", "no", "non"]:
            return False
        else:
            print_error("Answer with 'y' (yes) or 'n' (no)")


def get_model_config(model_type, model_name):
    print(f"\n=== {model_name} model configuration ===")
    model_id = get_model_id(model_name)
    model_provider = get_model_provider(model_name)
    api_key = get_model_api_key(model_name)
    model_full_name = get_model_name(model_name)
    model_aliases = get_model_aliases(model_name)
    api_url = get_model_api_url(model_name, model_provider)

    return {
        "id": model_id,
        "type": model_type,
        "aliases": model_aliases,
        "clients": [{"model": model_full_name, "type": model_provider, "args": {"api_key": api_key, "api_url": api_url, "timeout": 120}}],
    }


def get_model_api_url(model_name, model_provider):
    default_url = DEFAULT_URLS.get(model_provider, "")
    api_url = input(f"API URL for {model_name} [{default_url}]: ").strip()
    if not api_url:
        api_url = default_url
    return api_url


def get_model_aliases(model_name):
    model_aliases = input(f"Model aliases {model_name} []: ").strip().lower()
    if not model_aliases:
        model_aliases = []
    return model_aliases


def get_model_name(model_name):
    while True:
        model_full_name = input(f"Model name {model_name}: ").strip()
        if model_full_name:
            return model_full_name
        else:
            print_error("Error: model name is required")


def get_model_api_key(model_name):
    while True:
        api_key = input(f"API key for {model_name}: ").strip()
        if api_key:
            return api_key
        else:
            print_error("Error: API key is required")


def get_model_provider(model_name):
    while True:
        print("Available types: \033[1m" + ", ".join(DEFAULT_URLS.keys()) + "\033[0m")
        model_provider = input(f"Model type {model_name} [openai]: ").strip().lower()
        if not model_provider:
            model_provider = "openai"
        if model_provider in ["albert", "openai"]:
            return model_provider
        else:
            print_error("Error: model type must be one of: " + ", ".join(DEFAULT_URLS.keys()))


def get_model_id(model_name):
    while True:
        model_id = input(f"Model ID {model_name}: ").strip()
        if model_id:
            return model_id
        print_error("Error: model id is required")


def print_error(message: str):
    print(f"\033[91m{message}\033[0m")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\033[91mConfiguration file generation interrupted\033[0m")
