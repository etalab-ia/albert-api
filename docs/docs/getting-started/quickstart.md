# 🚀 Quickstart

Deploy OpenGateLLM quickly with Docker connected to our own free model and start using it:

```bash
git clone git@github.com:etalab-ia/OpenGateLLM.git
cd OpenGateLLM
make quickstart
```

ℹ️ **Info :** It will copy the `config.example.yml` and `.env.example` files into `config.yml` and `.env` files if they don't already exist.

Test the API:

```bash
curl -X POST "http://localhost:8080/v1/chat/completions" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer changeme" \
-d '{"model": "albert-testbed", "messages": [{"role": "user", "content": "Hello, how are you?"}]}'
```

The default master API key is `changeme`.

## User interface

A user interface is available at: http://localhost:8081/playground

> User: master
>
> Password: changeme

## Create a first user

```bash
make create-user
```

## Configure your models and add features

With configuration file, you can connect to your own models and add addtionnal services to OpenGateLLM.
Start by creating a configuration file and a .env dedicated:

```bash
cp config.example.yml config.yml
cp .env.example .env
```

Check the [configuration documentation](configuration.md) to configure your configuration file.

Vou can then set your environment variables in .env according to your needs.

You can run the services you need by running:

```bash
docker compose --env-file .env up <services_you_need> --detach
```

For instance:

```bash
docker compose --env-file .env up api playground postgres redis elasticsearch secretiveshell --detach
```
