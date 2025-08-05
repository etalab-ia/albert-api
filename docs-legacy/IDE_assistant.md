<h1 align="center">Using a code model in an IDE </h1>

**Objective**: Implement a code wizard on your : VS Code, ...

---
---

<h2>Continue, VScode assistant</h1>


<p style="text-align: justify;">Continue is a VS Code plugin that allows you to get a code wizard locally, on your IDE. </p>


---
### Continue : Installation 

- Open VS Code marketplace extensions.

- Search for `Continue` in the marketplace.

- Select and install `Continue - Codestral, Claude, and more`.

- If the installation was successful, you should see a "🗸 Continue" item in the bottom right-hand corner of your screen.

- After installation, you need to access the Continue config file. To do this:
  
Open Continue

Click on the selected model, this will open a drop-down menu allowing you to click on "Add Chat model".

A page will open below, click on "config file".

- Copy and paste the block below into config.yml, add your API key and save:

(otherwise accessible via the hidden `.continue` folder)


```yaml
name: Local Assistant
version: 1.0.0
schema: v1
models:
  - name: Albert code
    provider: openai
    model: albert-code
    apiBase: https://albert.api.etalab.gouv.fr/v1
    apiKey: <YOUR_API_KEY>
    roles:
      - chat

context:
  - provider: code
  - provider: docs-legacy
  - provider: diff
  - provider: terminal
  - provider: problems
  - provider: folder
  - provider: codebase
  
```

You now see Local Assistant as an available template in the chat window.


<h2>ProxyAI, Intellij/Pycharm assistant</h1>


<p style="text-align: justify;">ProxyAI is a Intellij/Pycharm plugin that allows you to get a code wizard locally, on your IDE. </p>


- Open Intellij/Pycharm marketplace extensions.

- Search for `ProxyAI` in the marketplace.

- Select and install.

- If the installation was successful, you should see a "ProxyAI" item in the tool configuration.

- After installation, you need to access the ProxyAI config file. To do this:
  
Open Tool > ProxyAI > Providers    
Select `Custom OpenAI`  
Add a new configuration `+`  
Change the configuration:  


```yaml
name: Albert code
API Key: <YOUR_API_KEY>
URL: https://albert.api.etalab.gouv.fr/v1/chat/completions
model: albert-code
```

You now see Albert-code in proxyAI.


<h2>Zed Editor</h1>


<p style="text-align: justify;">Zed Editor is a code editor providing native custom IA agent providers.</p>


- Open the Zed Agent Panel
- Open the Model drop-drown menu and select "Configure"
- Select the provider OpenAI
- Input your Albert API Key
- Input the custom API URL : https://albert.api.etalab.gouv.fr/v1
- Then in the main Zed Menu, click on "Open Settings"
- In the `"language models"` add the provider `"openai"` :

```json


"language models: {
    
    // maybe other models here

    "openai": {
      "api_url": "https://albert.api.etalab.gouv.fr/v1",  // this should be automatically inserted
      "api_key": "YOUR_ALBERT_API_KEY",                   // if not saved by the input from the Agent Panel
      "role": "chat",
      "available_models": [
        {
          "name": "albert-code-beta",
          "display_name": "Albert Code Beta",
          "supports_tools": true,
          "max_tokens": 128000
        }
      ],
      "version": "1"
    }
  }
}
```
