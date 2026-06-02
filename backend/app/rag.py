from __future__ import annotations

from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq

from .config import settings


SYSTEM_PROMPT = (
    "You are a helpful assistant for answering questions only from the supplied context. "
)


class RAGService:
    def __init__(self, vector_store) -> None:
        self.vector_store = vector_store
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to backend/.env before starting the app.")

        self.llm = ChatGroq(model=settings.groq_model, api_key=settings.groq_api_key, temperature=0.2)
        self.contextualize_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Rewrite the latest user question so it can be answered without prior chat history. Do not answer it."),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        self.answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                MessagesPlaceholder("chat_history"),
                ("human", "Context:\n{context}\n\nQuestion:\n{input}"),
            ]
        )
        self.retriever = vector_store.as_retriever(search_kwargs={"k": settings.top_k})
        self.history_aware_retriever = create_history_aware_retriever(self.llm, self.retriever, self.contextualize_prompt)
        self.document_chain = create_stuff_documents_chain(self.llm, self.answer_prompt)
        self.retrieval_chain = create_retrieval_chain(self.history_aware_retriever, self.document_chain)

    def answer(self, question: str, chat_history):
        return self.retrieval_chain.invoke({"input": question, "chat_history": chat_history})
