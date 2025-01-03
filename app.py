import os
from pathlib import Path
import requests
import shutil
import subprocess

os.environ["GIT_CLONE_PROTECTION_ACTIVE"] = "false"

# fetch model configuration
config_shared_path = Path("../../utils/llm_config.py")
config_dst_path = Path("llm_config.py")

if not config_dst_path.exists():
    if config_shared_path.exists():
        try:
            os.symlink(config_shared_path, config_dst_path)
        except Exception:
            shutil.copy(config_shared_path, config_dst_path)
    else:
        r = requests.get(url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/utils/llm_config.py")
        with open("llm_config.py", "w", encoding="utf-8") as f:
            f.write(r.text)
elif not os.path.islink(config_dst_path):
    if config_shared_path.exists():
        shutil.copy(config_shared_path, config_dst_path)
    else:
        r = requests.get(url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/utils/llm_config.py")
        with open("llm_config.py", "w", encoding="utf-8") as f:
            f.write(r.text)

## login to huggingfacehub to get access to pretrained model
from huggingface_hub import notebook_login, whoami

try:
    whoami('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')
except OSError:
    notebook_login()

#Choose Model Language
from llm_config import SUPPORTED_LLM_MODELS

model_languages = list(SUPPORTED_LLM_MODELS)

model_language = {
    "options": model_languages,
    "value": model_languages[0],
    "description": "Model Language:",
    "disabled": False
}

#Select model for inference
model_ids = list(SUPPORTED_LLM_MODELS[model_language["value"]])

model_id = {
    "options":model_ids,
    "value":model_ids[1],
    "description":"Model:",
    "disabled":False,
}

model_configuration = SUPPORTED_LLM_MODELS[model_language["value"]][model_id["value"]]
print(f"Selected model {model_id['value']}")

#Weights Compression using Optimum-CLI
prepare_int4_model = {
    "value":True,
    "description":"Prepare INT4 model",
    "disabled":False
}
prepare_int8_model = {
    "value":False,
    "description":"Prepare INT8 model",
    "disabled":False,
}
prepare_fp16_model = {
    "value":False,
    "description":"Prepare FP16 model",
    "disabled":False,
}
enable_awq = {
    "value": False,
    "description": "Enable AWQ",
    "disabled": not prepare_int4_model["value"]  # Placeholder for the actual condition
}

#INT4 compressession Of the Model--
from pathlib import Path

pt_model_id = model_configuration["model_id"]
pt_model_name = model_id["value"].split("-")[1]
fp16_model_dir = Path(model_id["value"]) / "FP16"
int8_model_dir = Path(model_id["value"]) / "INT8_compressed_weights"
int4_model_dir = Path(model_id["value"]) / "INT4_compressed_weights"

def convert_to_fp16():
    if (fp16_model_dir / "openvino_model.xml").exists():
        return
    remote_code = model_configuration.get("remote_code", False)
    export_command_base = "optimum-cli export openvino --model {} --task text-generation-with-past --weight-format fp16".format(pt_model_id)
    if remote_code:
        export_command_base += " --trust-remote-code"
    export_command = export_command_base + " " + str(fp16_model_dir)
    result = subprocess.run(export_command, shell=True, check=True, capture_output=True, text=True)
    
    # Print the output of the command (for debugging purposes)
    print(result.stdout)
    print(result.stderr)

def convert_to_int8():
    if (int8_model_dir / "openvino_model.xml").exists():
        return
    int8_model_dir.mkdir(parents=True, exist_ok=True)
    remote_code = model_configuration.get("remote_code", False)
    export_command_base = "optimum-cli export openvino --model {} --task text-generation-with-past --weight-format int8".format(pt_model_id)
    if remote_code:
        export_command_base += " --trust-remote-code"
    export_command = export_command_base + " " + str(int8_model_dir)
    result = subprocess.run(export_command, shell=True, check=True, capture_output=True, text=True)
    
    # Print the output of the command (for debugging purposes)
    print(result.stdout)
    print(result.stderr)

def convert_to_int4():
    compression_configs = {
        "zephyr-7b-beta": {
            "sym": True,
            "group_size": 64,
            "ratio": 0.6,
        },
        "mistral-7b": {
            "sym": True,
            "group_size": 64,
            "ratio": 0.6,
        },
        "minicpm-2b-dpo": {
            "sym": True,
            "group_size": 64,
            "ratio": 0.6,
        },
        "gemma-2b-it": {
            "sym": True,
            "group_size": 64,
            "ratio": 0.6,
        },
        "notus-7b-v1": {
            "sym": True,
            "group_size": 64,
            "ratio": 0.6,
        },
        "neural-chat-7b-v3-1": {
            "sym": True,
            "group_size": 64,
            "ratio": 0.6,
        },
        "llama-2-chat-7b": {
            "sym": True,
            "group_size": 128,
            "ratio": 0.8,
        },
        "llama-3-8b-instruct": {
            "sym": True,
            "group_size": 128,
            "ratio": 0.8,
        },
        "gemma-7b-it": {
            "sym": True,
            "group_size": 128,
            "ratio": 0.8,
        },
        "chatglm2-6b": {
            "sym": True,
            "group_size": 128,
            "ratio": 0.72,
        },
        "qwen-7b-chat": {"sym": True, "group_size": 128, "ratio": 0.6},
        "red-pajama-3b-chat": {
            "sym": False,
            "group_size": 128,
            "ratio": 0.5,
        },
        "default": {
            "sym": False,
            "group_size": 128,
            "ratio": 0.8,
        },
    }

    model_compression_params = compression_configs.get(model_id["value"], compression_configs["default"])
    if (int4_model_dir / "openvino_model.xml").exists():
        return
    remote_code = model_configuration.get("remote_code", False)
    export_command_base = "optimum-cli export openvino --model {} --task text-generation-with-past --weight-format int4".format(pt_model_id)
    int4_compression_args = " --group-size {} --ratio {}".format(model_compression_params["group_size"], model_compression_params["ratio"])
    if model_compression_params["sym"]:
        int4_compression_args += " --sym"
    if enable_awq["value"]:
        int4_compression_args += " --awq --dataset wikitext2 --num-samples 128"
    export_command_base += int4_compression_args
    if remote_code:
        export_command_base += " --trust-remote-code"
    export_command = export_command_base + " " + str(int4_model_dir)
    result = subprocess.run(export_command, shell=True, check=True, capture_output=True, text=True)
    
    # Print the output of the command (for debugging purposes)
    print(result.stdout)
    print(result.stderr)

if prepare_fp16_model["value"]:
    convert_to_fp16()
if prepare_int8_model["value"]:
    convert_to_int8()
if prepare_int4_model["value"]:
    convert_to_int4()

fp16_weights = fp16_model_dir / "openvino_model.bin"
int8_weights = int8_model_dir / "openvino_model.bin"
int4_weights = int4_model_dir / "openvino_model.bin"

if fp16_weights.exists():
    print(f"Size of FP16 model is {fp16_weights.stat().st_size / 1024 / 1024:.2f} MB")
for precision, compressed_weights in zip([8, 4], [int8_weights, int4_weights]):
    if compressed_weights.exists():
        print(f"Size of model with INT{precision} compressed weights is {compressed_weights.stat().st_size / 1024 / 1024:.2f} MB")
    if compressed_weights.exists() and fp16_weights.exists():
        print(f"Compression rate for INT{precision} model: {fp16_weights.stat().st_size / compressed_weights.stat().st_size:.3f}")

#Select device for inference and model variant--
import openvino as ov

core = ov.Core()
support_devices = core.available_devices
if "NPU" in support_devices:
    support_devices.remove("NPU")

device = {
    "options": support_devices + ["AUTO"],
    "value": "CPU",
    "description": "Device:",
    "disabled": False
}

available_models = []
if int4_model_dir.exists():
    available_models.append("INT4")
if int8_model_dir.exists():
    available_models.append("INT8")
if fp16_model_dir.exists():
    available_models.append("FP16")

model_to_run = {
    "options": available_models,
    "value": available_models[0],
    "description": "Model to run:",
    "disabled": False
}

#Instantiate Model using Optimum Intel
from transformers import AutoModelForCausalLM
from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer, pipeline
from transformers import AutoConfig, AutoTokenizer

model_id = "distilgpt2"
model = AutoModelForCausalLM.from_pretrained(model_id)
model = OVModelForCausalLM.from_pretrained(model_id, export=True)

if model_to_run["value"] == "INT4":
    model_dir = int4_model_dir
elif model_to_run["value"] == "INT8":
    model_dir = int8_model_dir
else:
    model_dir = fp16_model_dir
print(f"Loading model from {model_dir}")

ov_config = {"PERFORMANCE_HINT": "LATENCY", "NUM_STREAMS": "1", "CACHE_DIR": ""}

if "GPU" in device["value"] and "tiny-llama-1b-chat" in model_id["value"]:
    ov_config["GPU_ENABLE_SDPA_OPTIMIZATION"] = "NO"


if model_id == "distilgpt2" and "CPU" in core.available_devices and device["value"] in ["CPU", "AUTO"]:
    ov_config["INFERENCE_PRECISION_HINT"] = "f32"

model_name = model_configuration["model_id"]
tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)

ov_model = OVModelForCausalLM.from_pretrained(
    model_dir,
    device=device["value"],
    ov_config=ov_config,
    config=AutoConfig.from_pretrained(model_dir, trust_remote_code=True),
    trust_remote_code=True,
)

tokenizer_kwargs = model_configuration.get("tokenizer_kwargs", {})
test_string = "9*2="
input_tokens = tok(test_string, return_tensors="pt", **tokenizer_kwargs)
answer = ov_model.generate(**input_tokens, max_new_tokens=2)
print(tok.batch_decode(answer, skip_special_tokens=True)[0])

#For User Inerface
import torch
from threading import Event, Thread
from uuid import uuid4
from typing import List, Tuple
import gradio as gr
from transformers import (
    AutoTokenizer,
    StoppingCriteria,
    StoppingCriteriaList,
    TextIteratorStreamer,
)

model_id="distilgpt2"
model_name = model_configuration["model_id"]
start_message = model_configuration["start_message"]
history_template = model_configuration.get("history_template")
current_message_template = model_configuration.get("current_message_template")
stop_tokens = model_configuration.get("stop_tokens")
tokenizer_kwargs = model_configuration.get("tokenizer_kwargs", {})

max_new_tokens = 256

class StopOnTokens(StoppingCriteria):
    def __init__(self, token_ids):
        self.token_ids = token_ids

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        for stop_id in self.token_ids:
            if input_ids[0][-1] == stop_id:
                return True
        return False

if stop_tokens is not None:
    if isinstance(stop_tokens[0], str):
        stop_tokens = tok.convert_tokens_to_ids(stop_tokens)

    stop_tokens = [StopOnTokens(stop_tokens)]

def default_partial_text_processor(partial_text: str, new_text: str):

    partial_text += new_text
    return partial_text

text_processor = model_configuration.get("partial_text_processor", default_partial_text_processor)

def convert_history_to_token(history: List[Tuple[str, str]]):
    if pt_model_name == "baichuan2":
        system_tokens = tok.encode(start_message)
        history_tokens = []
        for old_query, response in history[:-1]:
            round_tokens = []
            round_tokens.append(195)
            round_tokens.extend(tok.encode(old_query))
            round_tokens.append(196)
            round_tokens.extend(tok.encode(response))
            history_tokens = round_tokens + history_tokens
        input_tokens = system_tokens + history_tokens
        input_tokens.append(195)
        input_tokens.extend(tok.encode(history[-1][0]))
        input_tokens.append(196)
        input_token = torch.LongTensor([input_tokens])
    elif history_template is None:
        messages = [{"role": "system", "content": start_message}]
        for idx, (user_msg, model_msg) in enumerate(history):
            if idx == len(history) - 1 and not model_msg:
                messages.append({"role": "user", "content": user_msg})
                break
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if model_msg:
                messages.append({"role": "assistant", "content": model_msg})

        input_token = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_tensors="pt")
    else:
        text = start_message + "".join(
            ["".join([history_template.format(num=round, user=item[0], assistant=item[1])]) for round, item in enumerate(history[:-1])]
        )
        text += "".join(
            [
                "".join(
                    [
                        current_message_template.format(
                            num=len(history) + 1,
                            user=history[-1][0],
                            assistant=history[-1][1],
                        )
                    ]
                )
            ]
        )
        input_token = tok(text, return_tensors="pt", **tokenizer_kwargs).input_ids
    return input_token

def user(message, history):
    return "", history + [[message, ""]]

def bot(history, conversation_id):
    temperature=0.5
    input_ids = convert_history_to_token(history)
    if input_ids.shape[1] > 2000:
        history = [history[-1]]
        input_ids = convert_history_to_token(history)
    streamer = TextIteratorStreamer(tok, timeout=30.0, skip_prompt=True, skip_special_tokens=True)
    generate_kwargs = dict(
        input_ids=input_ids,
        max_new_tokens=300,
        temperature=0.5,
        do_sample=temperature > 0.0,
        top_p=1.0,
        top_k=50,
        repetition_penalty=1.1,
        streamer=streamer,
    )
    if stop_tokens is not None:
        generate_kwargs["stopping_criteria"] = StoppingCriteriaList(stop_tokens)

    stream_complete = Event()

    def generate_and_signal_complete():
        global start_time
        ov_model.generate(**generate_kwargs)
        stream_complete.set()

    t1 = Thread(target=generate_and_signal_complete)
    t1.start()

    partial_text = ""
    for new_text in streamer:
        partial_text = text_processor(partial_text, new_text)
        history[-1][1] = partial_text
        yield history

def request_cancel():
    ov_model.request.cancel()

def get_uuid():
    return str(uuid4())

with gr.Blocks(
    theme=gr.themes.Soft(),
    css=".disclaimer {font-variant-caps: all-small-caps;}",
) as demo:
    conversation_id = gr.State(get_uuid)
    gr.Markdown(f"""<h1><center>OpenVINO J&S Chatbot</center></h1>""")
    chatbot = gr.Chatbot(height=500)
    with gr.Row():
        with gr.Column():
            msg = gr.Textbox(
                label="Chat Message Box",
                placeholder="Chat Message Box",
                show_label=False,
                container=False,
            )
        with gr.Column():
            with gr.Row():
                submit = gr.Button("Submit")
                stop = gr.Button("Stop")
                clear = gr.Button("Clear")

    submit_event = msg.submit(
        fn=user,
        inputs=[msg, chatbot],
        outputs=[msg, chatbot],
        queue=False,
    ).then(
        fn=bot, inputs=[chatbot, conversation_id], outputs=chatbot,queue=True,
    )
    submit_click_event = submit.click(
        fn=user,inputs=[msg, chatbot],outputs=[msg, chatbot], queue=False,
    ).then(
        fn=bot,inputs=[chatbot, conversation_id],outputs=chatbot,queue=True,
    )
    stop.click(
        fn=request_cancel, inputs=None,outputs=None, cancels=[submit_event, submit_click_event], queue=False,
    )
    clear.click(lambda: None, None, chatbot, queue=False)

demo.launch(share=True)
