# Local LLM (lollm)

This app allows you to send iMessages to the genAI models running in your own computer.
See it in action here.

<< insert video >>

This project uses Docker compose to run the required services locally.
It uses [sendblue](https://sendblue.co/) to handle iMessages and [ollama](https://ollama.ai/) to install and manage AI models.

If you add an OpenAI key you can also use [ChatGPT](https://openai.com/).

## Usage

You use the app by sending messages to the bot.
See the setup instructions on how to configure sendblue.

There is a `/help` message that lists available commands.
Some examples include:
```
/help - list help commands
/list - list available models
/install - install a model from ollama
/default - set a default model
```
Message the Bot with any text.
![messaging the bot with the question "what is the air speed velocity of a swallow"](/img/lollm-demo-1.gif)

## Setup
