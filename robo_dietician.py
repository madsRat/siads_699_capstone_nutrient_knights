import streamlit as st
import os
import pandas as pd

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


def run_Robo_Dietitian(input_value):
    # initialize chat history
    setup_prompt =  """You are an expert dietitian. You respond to human diet related queries. Ask relevant counter questions to get additional information where necessary. 
        Politely refuse to answer questions that are not related to human diet. Mention that you are an AI dietitian and recommend user to review the responses 
        with a human expert. Use three sentences maximum and keep the answer concise. Include 2-3 suggestions in response to the query if possible.
        Consider the following patient information: \n\n"""

    system_prompt = setup_prompt + input_value

    if "messages" not in st.session_state:
        st.session_state.messages = []

        st.session_state.messages.append(SystemMessage(system_prompt))
        st.write("Hello 👋. I am a chatbot here to answer any question's about your patients nutritional needs.")

    # display chat messages from history on app rerun
    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.markdown(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(message.content)

    # create the bar where we can type messages
    prompt = st.chat_input("Ask me a question about patient diet")

    # did the user submit a prompt?
    if prompt:

        # add the message from the user (prompt) to the screen with streamlit
        with st.chat_message("user"):
            st.markdown(prompt)

            st.session_state.messages.append(HumanMessage(prompt))

        # initialize the llm
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0,api_key=os.environ.get("OPENAI_API_KEY"))

        st.session_state.messages.append(SystemMessage(system_prompt))

        # invoking the llm
        result = llm.invoke(st.session_state.messages).content

        # adding the response from the llm to the screen (and chat)
        with st.chat_message("assistant"):
            st.markdown(result)

            st.session_state.messages.append(AIMessage(result))

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        input_value = sys.argv[1]
    else:
        input_value = ""
    run_Robo_Dietitian(input_value)

# TODO implement above to incldue arguments in command line run in main.py