#!/usr/bin/env python3
import sys
import os
import yaml

MODEL_TYPES = {
    "text-embeddings-inference": "Text Embeddings",
    "text-classification": "Classification de Texte",
    "automatic-speech-recognition": "Reconnaissance Vocale",
    "text-generation": "Génération de Texte",
}

CONFIG_FILE = "config_tmp.yml"

DEFAULT_URLS = {"openai": "https://api.openai.com/v1", "albert": "https://api.albert.fr/v1"}


def main():
    print("\n" + "=" * 60)
    print("CONFIGURATION DES MODÈLES IA")
    print("=" * 60)
    models_configuration = ask_models_configuration()
    existing_config = get_existing_configuration()
    write_models_configuration(existing_config, models_configuration)
    display_configuration_summary(models_configuration)


def ask_models_configuration():
    models = []
    for model_type, display_name in MODEL_TYPES.items():
        question = f"Voulez-vous ajouter un modèle de type {display_name} ({model_type}) ?"

        if ask_yes_no(question):
            while True:
                try:
                    count = input(f"Combien de modèles {display_name} voulez-vous ajouter ? [1]: ").strip()
                    if not count:
                        count = 1
                    else:
                        count = int(count)

                    if count < 1:
                        print("Le nombre doit être au moins 1")
                        continue
                    break
                except ValueError:
                    print("Veuillez entrer un nombre valide")

            for i in range(count):
                suffix = f" #{i + 1}" if count > 1 else ""
                model_config = get_model_config(model_type, f"{display_name}{suffix}")
                models.append(model_config)
    return models


def get_existing_configuration():
    existing_config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                existing_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Erreur lors de la lecture de config.yml: {e}")
            existing_config = {}
    return existing_config


def write_models_configuration(existing_config, models_configuration):
    existing_config["models"] = models_configuration
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(existing_config, f, default_flow_style=False, indent=2, allow_unicode=True, sort_keys=False)


def display_configuration_summary(models_configuration):
    print(f"\n✅ Configuration sauvegardée dans config.yml avec {len(models_configuration)} modèle(s)")
    if models_configuration:
        print("\n" + "=" * 40)
        print("RÉSUMÉ DE LA CONFIGURATION")
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
            print("Veuillez répondre par 'y' (oui) ou 'n' (non)")


def get_model_config(model_type, model_name):
    print(f"\n=== Configuration du modèle {model_name} ===")
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
    api_url = input(f"URL de l'API pour {model_name} [{default_url}]: ").strip()
    if not api_url:
        api_url = default_url
    return api_url


def get_model_aliases(model_name):
    model_aliases = input(f"Alias du modèle {model_name} []: ").strip().lower()
    if not model_aliases:
        model_aliases = []
    return model_aliases


def get_model_name(model_name):
    model_full_name = input(f"Nom du modèle {model_name}: ").strip()
    if not model_full_name:
        print("Erreur: Le nom du modèle est requis")
        sys.exit(1)
    return model_full_name


def get_model_api_key(model_name):
    api_key = input(f"Clé API pour {model_name}: ").strip()
    if not api_key:
        print("Erreur: La clé API est requise")
        sys.exit(1)
    return api_key


def get_model_provider(model_name):
    print("Types disponibles: " + ", ".join(DEFAULT_URLS.keys()))
    model_provider = input(f"Type du modèle {model_name} [openai]: ").strip().lower()
    if not model_provider:
        model_provider = "openai"
    if model_provider not in ["albert", "openai"]:
        print("Erreur: Le type doit être 'albert' ou 'openai'")
        sys.exit(1)
    return model_provider


def get_model_id(model_name):
    model_id = input(f"ID du modèle {model_name}: ").strip()
    if not model_id:
        print("Erreur: L'ID du modèle est requis")
        sys.exit(1)
    return model_id


if __name__ == "__main__":
    main()
