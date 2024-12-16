import html
import re

import streamlit as st
from langchain.callbacks.base import BaseCallbackHandler
from utils import pc


def format_message(text):
    """
    Formats the messages in the chatbot UI, preserving code blocks, inline code, bold, italic, links, and newlines.

    Parameters:
    text (str): The text to be formatted.

    Returns:
    str: The formatted HTML-safe text.
    """
    # Regex for capturing blocks of code and URLs
    pattern = r"(```[\s\S]*?```|:url_start:.*?:url_end:|`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)"
    segments = re.split(pattern, text)

    formatted_text = ""

    for segment in segments:
        if not segment:
            continue
        segment = segment.replace("\n\n", "\n")

        if segment.startswith("```") and segment.endswith("```"):
            # Code block
            code_content = segment[3:-3].strip()  # Remove ``` delimiters
            formatted_text += '<pre style="white-space: pre-wrap; word-wrap: break-word;">' f"<code>{html.escape(code_content)}</code>" "</pre>"
        elif segment.startswith(":url_start:") and segment.endswith(":url_end:"):
            # URL block
            url_content = segment[11:-9]  # Remove :url_start: and :url_end:
            urls_couple = url_content.split(" ---- ")
            if len(urls_couple) == 2:
                # Clickable text + URL
                formatted_text += f'<a href="{html.escape(urls_couple[1])}">{html.escape(urls_couple[0])}</a>'
            else:
                # If format is invalid, escape the entire segment
                formatted_text += html.escape(segment)
        elif segment.startswith("`") and segment.endswith("`"):
            # Inline code
            inline_code = segment[1:-1]  # Remove ` delimiters
            formatted_text += f'<code style="background: #f4f4f4; padding: 2px 4px; border-radius: 4px;">{html.escape(inline_code)}</code>'
        elif (segment.startswith("**") and segment.endswith("**")) or (segment.startswith("__") and segment.endswith("__")):
            # Bold text
            bold_text = segment[2:-2]  # Remove ** or __ delimiters
            formatted_text += f"<strong>{html.escape(bold_text)}</strong>"
        elif (segment.startswith("*") and segment.endswith("*")) or (segment.startswith("_") and segment.endswith("_")):
            # Italic text
            italic_text = segment[1:-1]  # Remove * or _ delimiters
            formatted_text += f"<em>{html.escape(italic_text)}</em>"
        else:
            # Plain text, replace newlines with <br>
            formatted_text += html.escape(segment).replace("\n", "<br>")

    return formatted_text


## Simpler but weaker
# def format_message(text):
#    return markdown.markdown(text.replace("\n\n\n", "\n\n"))


def message_func(text, is_user=False, is_df=False, model="gpt"):
    """
    This function is used to display the messages in the chatbot UI.

    Parameters:
    text (str): The text to be displayed.
    is_user (bool): Whether the message is from the user or not.
    is_df (bool): Whether the message is a dataframe or not.
    """
    model_url = "kokoko"

    avatar_url = "https://cdn-icons-png.flaticon.com/256/4712/4712109.png"
    if is_user:
        avatar_url = "https://icons.veryicon.com/png/o/miscellaneous/two-color-icon-library/user-286.png"
        message_alignment = "flex-end"
        message_bg_color = f"linear-gradient(135deg, #8585f6 0%, {pc} 40%)"
        avatar_class = "user-avatar"
        st.write(
            f"""
                <div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: {message_alignment};">
                    <div style="background: {message_bg_color}; color: white; border-radius: 20px; padding: 10px; margin-right: 5px; max-width: 75%; font-size: 14px;">
                        {text} \n </div>
                    <img src="{avatar_url}" class="{avatar_class}" alt="avatar" style="width: 40px; height: 40px;" />
                </div>
                """,
            unsafe_allow_html=True,
        )
    else:
        message_alignment = "flex-start"
        message_bg_color = "00FFFFFF"  # Transparent
        avatar_class = "bot-avatar"

        if is_df:
            st.write(
                f"""
                    <div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: {message_alignment};">
                        <img src="{model_url}" class="{avatar_class}" alt="avatar" style="width: 50px; height: 50px;" />
                    </div>
                    """,
                unsafe_allow_html=True,
            )
            st.write(text)
            return
        else:
            text = format_message(text)

        st.write(
            f"""
                <div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: {message_alignment};">
                    <img src="{avatar_url}" class="{avatar_class}" alt="avatar" style="width: 30px; height: 30px;" />
                    <div style="background: {message_bg_color}; color: white; border-radius: 20px; padding: 10px; margin-right: 5px; margin-left: 5px; max-width: 75%; font-size: 14px;">
                        {text} \n </div>
                </div>
                """,
            unsafe_allow_html=True,
        )


class StreamlitUICallbackHandler(BaseCallbackHandler):
    def __init__(self, model):
        self.token_buffer = []
        self.placeholder = st.empty()
        self.has_streaming_ended = False
        self.has_streaming_started = False
        self.model = model
        self.avatar_url = "https://cdn-icons-png.flaticon.com/256/4712/4712109.png"

    def start_loading_message(self):
        loading_message_content = self._get_bot_message_container("...")
        self.placeholder.markdown(loading_message_content, unsafe_allow_html=True)

    def print_tmp(self, text):
        loading_message_content = self._get_bot_message_container(text)
        self.placeholder.markdown(loading_message_content, unsafe_allow_html=True)

    def on_llm_new_token(self, token, run_id, parent_run_id=None, **kwargs):
        if not self.has_streaming_started:
            self.has_streaming_started = True

        self.token_buffer.append(token)
        complete_message = "".join(self.token_buffer)
        container_content = self._get_bot_message_container(complete_message)
        self.placeholder.markdown(container_content, unsafe_allow_html=True)

    def on_llm_end(self, response, run_id, parent_run_id=None, **kwargs):
        self.token_buffer = []
        self.has_streaming_ended = True
        self.has_streaming_started = False

    def put_response(self, text):
        self.placeholder.markdown(self._get_bot_message_container(text), unsafe_allow_html=True)

    def _get_bot_message_container(self, text):
        """Generate the bot's message container style for the given text."""
        formatted_text = format_message(text)
        container_content = f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: flex-start;">
                <img src="{self.avatar_url}" class="bot-avatar" alt="avatar" style="width: 30px; height: 30px;" />
                <div style="background: 00FFFFFF; color: white; border-radius: 20px; padding: 10px; margin-right: 5px; margin-left: 5px; max-width: 75%; font-size: 14px;">
                    {formatted_text} \n </div>
            </div>
        """
        return container_content

    def display_dataframe(self, df):
        """
        Display the dataframe in Streamlit UI within the chat container.
        """
        message_alignment = "flex-start"
        avatar_class = "bot-avatar"

        st.write(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px; justify-content: {message_alignment};">
                <img src="{self.avatar_url}" class="{avatar_class}" alt="avatar" style="width: 30px; height: 30px;" />
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write(df)

    def __call__(self, *args, **kwargs):
        pass
