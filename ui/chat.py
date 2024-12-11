import logging
import traceback

from openai import OpenAI
import requests
import streamlit as st
from style_ui import StreamlitUICallbackHandler, message_func
import streamlit_antd_components as sac


from config import BASE_URL
from utils import get_collections, get_models, set_config, authenticate, header

# Config
set_config()
API_KEY = authenticate()
header()

streamlit_style = """
			<style>
			@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@100&display=swap');

			html, body, [class*="css"]  {
			font-family: 'Roboto', sans-serif;
			}
			</style>
			"""
st.markdown(streamlit_style, unsafe_allow_html=True)
# Data
try:
    language_models, embeddings_models, _ = get_models(api_key=API_KEY)
    collections = get_collections(api_key=API_KEY)
except Exception:
    st.error("Error to fetch user data.")
    logging.error(traceback.format_exc())
    st.stop()

openai_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

hierarchy = {}
for item in language_models:
    parent, child = item.split("/")  # Parent/Child Separation
    if parent not in hierarchy:
        hierarchy[parent] = []  # Initialize children list
    hierarchy[parent].append(child)  # Add child


# Create CasItems from models list
def create_cas_items(data):
    items = []
    for parent, children in data.items():
        # Construct children if exist
        if children:
            children_items = [sac.CasItem(child, icon="child-icon") for child in children]
            items.append(sac.CasItem(parent, icon="parent-icon", children=children_items))
        else:
            items.append(sac.CasItem(parent, icon="parent-icon"))
    return items


# Contruct models list from hierarchy
cas_items = create_cas_items(hierarchy)

# Sidebar
with st.sidebar:
    params = {"sampling_params": dict(), "rag": dict()}
    st.title("Chat parameters")
    st.markdown("")
    st.markdown("Language model")
    params["sampling_params"]["model"] = "/".join(sac.cascader(items=cas_items, label="", index=[0, 1], multiple=False, search=True, clear=True))
    st.markdown("Temperature")
    params["sampling_params"]["temperature"] = st.slider(
        "Temperature", value=0.2, min_value=0.0, max_value=1.0, step=0.1, label_visibility="collapsed"
    )
    st.markdown("Max tokens")
    params["sampling_params"]["max_tokens"] = int(
        sac.segmented(
            items=[
                sac.SegmentedItem(label="128"),
                sac.SegmentedItem(label="256"),
                sac.SegmentedItem(label="512"),
                sac.SegmentedItem(label="1024"),
            ],
            label="",
            align="center",
            size="sm",
        )
    )
    print(params["sampling_params"]["max_tokens"])

    st.title("RAG parameters")
    st.markdown("")
    st.markdown("Embeddings model")
    params["rag"]["embeddings_model"] = st.selectbox("Embeddings model", sorted(embeddings_models), label_visibility="collapsed")
    model_collections = [
        f"{collection["name"]} - {collection["id"]}" for collection in collections if collection["model"] == params["rag"]["embeddings_model"]
    ] + ["Le net - internet"]
    if model_collections:
        st.markdown("Collections")
        selected_collections = st.multiselect(
            label="Collections", options=model_collections, default=[model_collections[0]], label_visibility="collapsed"
        )
        params["rag"]["collections"] = [collection.split(" - ")[1] for collection in selected_collections]
        st.markdown("Number of chunks to retrieve")
        params["rag"]["k"] = st.number_input("Top K", value=3, label_visibility="collapsed")

    if model_collections:
        rag = st.toggle("Activated RAG", value=True, disabled=not bool(params["rag"]["collections"]))
    else:
        rag = st.toggle("Activated RAG", value=False, disabled=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col2:
        new_chat = st.button("New chat", use_container_width=True)
    if new_chat:
        st.session_state.pop("messages", None)
        st.session_state.pop("sources", None)
        st.rerun()
    with col1:
        logout = st.button("⚠ Logout ", type="primary", use_container_width=True)
    if logout:
        st.session_state.pop("API_KEY")
        st.rerun()

with open("ui/styles.md", "r") as styles_file:
    styles_content = styles_file.read()

st.write(styles_content, unsafe_allow_html=True)

# Main

INITIAL_MESSAGE = [
    {"role": "user", "content": "Bonjour!"},
    {
        "role": "assistant",
        "content": """Bonjour ! Je suis Albert, et je peux vous aider si vous avez des questions administratives ! 🔍
        Je peux me connecter à vos bases de connaissances, pour ça sélectionnez les collections voulues dans le menu de gauche.
        Je peux également chercher sur les sites officiels de l'État, pour ça sélectionnez la collection "Internet" à gauche. Si vous ne souhaitez pas utiliser de collection, désactivez le RAG en décochant la fonction "Activated RAG".
        
        Comment puis-je vous aider ?
        """,
    },
]

model = ""
# Initialize the chat messages history
if "messages" not in st.session_state.keys():
    st.session_state["messages"] = INITIAL_MESSAGE

if "history" not in st.session_state:
    st.session_state["history"] = []

if "sources" not in st.session_state:
    st.session_state["sources"] = []

if "model" not in st.session_state:
    st.session_state["model"] = model

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

for message in st.session_state.messages:
    message_func(
        message["content"],
        True if message["role"] == "user" else False,
        True if message["role"] == "data" else False,
        model,
    )

callback_handler = StreamlitUICallbackHandler(model)


def generate_response_stream(messages):
    """
    Generate streaming response and save it as final answer.
    """
    final_message = ""

    try:
        for chunk in openai_client.chat.completions.create(stream=True, messages=messages, **params["sampling_params"]):
            if hasattr(chunk, "choices") and chunk.choices:
                choice = chunk.choices[0]
                if hasattr(choice, "delta") and hasattr(choice.delta, "content"):
                    token = choice.delta.content
                    final_message += token
                    callback_handler.on_llm_new_token(token, run_id="stream_run_id")
    except Exception as e:
        st.error(f"Une erreur est survenue lors du streaming : {e}")
        logging.error(traceback.format_exc())

    # End of stream
    callback_handler.on_llm_end(response="Fin de la réponse.", run_id="stream_run_id")
    # Save final answer
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    st.session_state["messages"].append({"role": "assistant", "content": final_message.strip()})
    return final_message


sources = st.session_state["sources"]
if "messages" in st.session_state and st.session_state["messages"][-1]["role"] != "assistant":
    user_input_content = st.session_state["messages"][-1]["content"]

    if isinstance(user_input_content, str):
        callback_handler.start_loading_message()
        try:
            if rag:
                data = {
                    "collections": params["rag"]["collections"],
                    "model": params["rag"]["embeddings_model"],
                    "k": params["rag"]["k"],
                    "prompt": user_input_content,
                    "score_threshold": None,
                }
                response = requests.post(
                    f"{BASE_URL}/search",
                    json=data,
                    headers={"Authorization": f"Bearer {API_KEY}"},
                )
                print(response.json())
                assert response.status_code == 200

                prompt_template = (
                    "Réponds à la question suivante de manière claire en te basant sur les documents ci-dessous : {prompt}\n\nDocuments :\n{chunks}"
                )
                chunks = "\n".join([result["chunk"]["content"] for result in response.json()["data"]])
                chunks_contents = [result["chunk"]["content"] for result in response.json()["data"]]
                sources = list(set(result["chunk"]["metadata"]["document_name"] for result in response.json()["data"]))
                try:
                    urls = list(set(result["chunk"]["metadata"]["url"] for result in response.json()["data"]))
                except Exception:
                    urls = sources
                prompt = prompt_template.format(prompt=user_input_content, chunks=chunks)
                messages = st.session_state["messages"][:-1] + [{"role": "user", "content": prompt}]
            else:
                messages = st.session_state["messages"]
                sources = []
            st.session_state["sources"] = sources
            answer = generate_response_stream(messages)

        except Exception as e:
            st.error(f"Erreur lors de la génération de la réponse : {e}")
            logging.error(traceback.format_exc())
        if sources:
            sac.tags(
                [
                    sac.Tag(label=source, icon="send" if "http" in url else "book", link=url if "http" in url else None)
                    for source, url in zip(sources, urls)
                ],
                align="left",
            )
        callback_handler.put_response(answer.strip())
