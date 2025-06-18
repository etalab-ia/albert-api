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
    apiBase: https://albert.api.dev.etalab.gouv.fr/v1
    apiKey: <YOUR_API_KEY>
    roles:
      - chat

context:
  - provider: code
  - provider: docs
  - provider: diff
  - provider: terminal
  - provider: problems
  - provider: folder
  - provider: codebase
  
```

You now see Local Assistant as an available template in the chat window.


<h2>ProxyAI, Intellij/Pycharm assistant</h1>


<p style="text-align: justify;">ProxyAI is a Intellij/Pycharm plugin that allows you to get a code wizard locally, on your IDE. </p>

