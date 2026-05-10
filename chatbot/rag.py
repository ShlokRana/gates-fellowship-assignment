"""RAG chain with conversation history."""
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from chatbot.prompts import CONDENSE_QUESTION_PROMPT, SYSTEM_PROMPT

load_dotenv()

_session_store: Dict[str, BaseChatMessageHistory] = {}


def _get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]


def build_chain(vectorstore_dir: Path):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    store = FAISS.load_local(
        str(vectorstore_dir), embeddings, allow_dangerous_deserialization=True
    )
    retriever = store.as_retriever(search_kwargs={"k": 3})

    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

    condense_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CONDENSE_QUESTION_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, condense_prompt
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    qa_chain = create_stuff_documents_chain(llm, qa_prompt)

    rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    conversational_chain = RunnableWithMessageHistory(
        rag_chain,
        _get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )
    return conversational_chain
