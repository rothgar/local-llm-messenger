import os, requests, time, openai, json, logging
from pprint import pprint
from typing import Union, List

from fastapi import FastAPI
from pydantic import BaseModel

from sendblue import Sendblue

SENDBLUE_API_KEY = os.environ.get("SENDBLUE_API_KEY")
SENDBLUE_API_SECRET = os.environ.get("SENDBLUE_API_SECRET")
openai.api_key = os.environ.get("OPENAI_API_KEY")
OLLAMA_API = os.environ.get("OLLAMA_API_ENDPOINT", "http://ollama:11434/api")
CALLBACK_URL = "https://s.gerbil-dragon.ts.net/callback"

sendblue = Sendblue(SENDBLUE_API_KEY, SENDBLUE_API_SECRET)

logger = logging.getLogger(__name__)

def set_default_model(model: str):
    try:
        with open("default.ai", "w") as f:
            f.write(model)
            f.close()
            return
    except IOError:
        logger.error("Could not open file")
        exit(1)


def get_default_model() -> str:
    try:
        with open("default.ai") as f:
            default = f.readline().strip("\n")
            f.close()
            if default != "":
                return default
            else:
                set_default_model("llama2:latest")
                return ""
    except IOError:
        logger.error("Could not open file")
        exit(1)


def validate_model(model: str) -> bool:
    available_models = get_model_list()
    if model in available_models:
        return True
    else:
        return False


def get_ollama_model_list() -> List[str]:
    available_models = []
    tags = requests.get(OLLAMA_API + "/tags")
    all_models = json.loads(tags.text)
    for model in all_models["models"]:
        available_models.append(model["name"])
    return available_models


def get_openai_model_list() -> List[str]:
    return ["gpt-3.5-turbo", "dall-e-2"]


def get_model_list() -> List[str]:
    ollama_models = []
    openai_models = []
    all_models = []
    if "OPENAI_API_KEY" in os.environ:
        # print(openai.Model.list())
        openai_models = get_openai_model_list()

    ollama_models = get_ollama_model_list()
    all_models = ollama_models + openai_models
    return all_models


DEFAULT_MODEL = get_default_model()

if DEFAULT_MODEL == '':
    # This is probably the first run so we need to install a model
    print("No model found. Installing llama2:latest")
    pull_data = '{"name": "llama2:latest","stream": false}'
    try:
        pull_resp = requests.post(OLLAMA_API + "/pull", data=pull_data)
        pull_resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)
    set_default_model("llama2:latest")
    DEFAULT_MODEL="llama2:latest"

if validate_model(DEFAULT_MODEL):
    logger.info("Using model: " + DEFAULT_MODEL)
else:
    logger.error("Model " + DEFAULT_MODEL + " not available.")
    logger.info(get_model_list())
    exit(1)


class Msg(BaseModel):
    accountEmail: str
    content: str
    media_url: str
    is_outbound: bool
    status: str
    error_code: int | None = None
    error_message: str | None = None
    message_handle: str
    date_sent: str
    date_updated: str
    from_number: str
    number: str
    to_number: str
    was_downgraded: bool | None = None
    plan: str


class Callback(BaseModel):
    accountEmail: str
    content: str
    is_outbound: bool
    status: str
    error_code: int | None = None
    error_message: str | None = None
    message_handle: str
    date_sent: str
    date_updated: str
    from_number: str
    number: str
    to_number: str
    was_downgraded: bool | None = None
    plan: str


def msg_openai(msg: Msg, model=DEFAULT_MODEL):
    """Sends a message to openai"""
    gpt_resp = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": msg.content + "in under 100 words"}],
    )
    append_context(gpt_resp.choices[0].message.content)
    msg_response = sendblue.send_message(
        msg.from_number,
        {
            "content": gpt_resp.choices[0].message.content,
            "status_callback": CALLBACK_URL,
        },
    )
    return


def msg_ollama(msg: Msg, model=DEFAULT_MODEL):
    """Sends a message to the ollama endpoint"""
    ollama_headers = {"Content-Type": "application/json"}
    ollama_data = (
        '{"model":"'
        + model
        + '", "stream": false, "prompt":"'
        + msg.content
        + ' in under 100 words"}'
    )
    ollama_resp = requests.post(
        OLLAMA_API + "/generate", headers=ollama_headers, data=ollama_data
    )
    response_dict = json.loads(ollama_resp.text)
    # pprint(response_dict)
    append_context(response_dict["response"])
    msg_response = sendblue.send_message(
        msg.from_number,
        {"content": response_dict["response"], "status_callback": CALLBACK_URL},
    )
    return


def send_typing_indicator(msg: Msg):
    """This just sends a typing indicator to let them know we're working on a reply"""
    # sendblue.send_typing_indicator(msg.from_number)
    sb_headers = {
        "sb-api-key-id": os.environ.get("SENDBLUE_API_KEY"),
        "sb-api-secret-key": os.environ.get("SENDBLUE_API_SECRET"),
        "Content-Type": "application/json",
    }
    typing_data = '{"number":"' + msg.from_number + '"}'
    typing_resp = requests.post(
        "https://api.sendblue.co/api/send-typing-indicator",
        headers=sb_headers,
        data=typing_data,
    )


def append_context(content: str):
    """Appends the current content to a file to send to the model with new requests"""
    f = open("context.txt", "a")
    f.write(content + "\n")
    f.close()
    f = open("context.txt", "r")
    context = f.readlines()
    trunk_context = context[-20:]
    f.close()
    f = open("context.txt", "w")
    for line in trunk_context:
        f.write(line)
    f.close()


def match_closest_model(model: str) -> str:
    """Match a model when provided incomplete info"""
    available_models = get_model_list()
    for this_model in available_models:
        if this_model.startswith(model):
            return this_model
    return ""


app = FastAPI()

print("OLLAMA API IS " + OLLAMA_API)


@app.post("/msg")
async def create_msg(msg: Msg):
    privided_model = ""
    logger.info(msg)

    # run commands
    if msg.content.startswith("/"):
        command(msg)
        return

    # change model via @ message
    if msg.content.startswith("@"):
        provided_model = msg.content.strip("@").lower().split(" ")[0]
        model = match_closest_model(provided_model)
        print("using temp model " + model + "from provided model " + provided_model)
        msg.content = " ".join(msg.content.split(" ")[1:])
    else:
        model = DEFAULT_MODEL

    if model == "":
        msg_response = sendblue.send_message(
            msg.from_number,
            {
                "content": "Model "
                + provided_model
                + " not found. Try one of these \n"
                + "\n".join(get_model_list()),
                "status_callback": CALLBACK_URL,
            },
        )
        return

    # Save media files
    if msg.media_url != "":
        r = requests.get(msg.media_url, allow_redirects=True)
        file_name = msg.media_url.split("/")[-1]
        with open("media/" + file_name, "wb") as f:
            print("saving file " + file_name)
            f.write(r.content)

    # don't run anything if there's no text
    if msg.content == "":
        return

    # write the content to our context file
    append_context(msg.content)
    send_typing_indicator(msg)

    # get the models to know which model we should use
    openai_models = get_openai_model_list()
    ollama_models = get_ollama_model_list()

    # The model should never be in both
    if model in openai_models:
        msg_openai(msg, model=model)
    if model in ollama_models:
        msg_ollama(msg, model=model)
    return


@app.post("/callback")
async def create_callback(callback: Callback):
    """This is a callback URL for sendblue. It doesn't do anything except
    return when sendblue sends a message status"""
    # TODO: make this track messages
    logger.info(callback)
    return


def command(msg: Msg):
    """This is for slash commands that can be helpful from within messages.
    None of these commands should interact with a model"""

    commands = ["help", "list", "install", "default"]
    cmd = msg.content.strip("/").lower().split(" ")[0]
    match cmd:
        case "help":
            help_response = sendblue.send_message(
                msg.from_number,
                {
                    "content": "Available commands:\n/" + "\n/".join(commands),
                    "status_callback": CALLBACK_URL,
                },
            )
        case "list":
            # list ai againts
            available_models = get_model_list()
            default_model = get_default_model()
            available_models = [
                m.replace(default_model, default_model + "*") for m in available_models
            ]
            list_response = sendblue.send_message(
                msg.from_number,
                {
                    "content": "Available models:\n" + "\n".join(available_models),
                    "status_callback": CALLBACK_URL,
                },
            )
        case "install":
            # install ollama
            args = msg.content.lower().split(" ")[1]
            pull_data = '{"name": "' + args + '","stream": false}'
            install_response = sendblue.send_message(
                msg.from_number,
                {"content": "Installing " + args, "status_callback": CALLBACK_URL},
            )
            try:
                pull_resp = requests.post(OLLAMA_API + "/pull", data=pull_data)
                pull_resp.raise_for_status()
            except requests.exceptions.HTTPError as err:
                raise SystemExit(err)
            done_response = sendblue.send_message(
                msg.from_number,
                {
                    "content": "Installed " + args + " Use it with /default",
                    "status_callback": CALLBACK_URL,
                },
            )
        case "default":
            # set default model
            args = msg.content.lower().split(" ")[1]
            matched_model = match_closest_model(args)
            print("setting default model " + matched_model)
            set_default_model(matched_model)
        case _:
            help_response = sendblue.send_message(
                msg.from_number,
                {
                    "content": "Command " + msg.content + " not available.",
                    "status_callback": CALLBACK_URL,
                },
            )
    return


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)