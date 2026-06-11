from __future__ import annotations

from typing import TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import END, START, StateGraph
from langchain_groq import ChatGroq

from .config import settings


SYSTEM_PROMPT = (
    "You are a helpful assistant for answering questions only from the supplied context. "
)


class RAGState(TypedDict, total=False):
    input: str
    chat_history: list[BaseMessage]
    standalone_question: str
    context: list[Document]
    answer: str


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
        workflow = StateGraph(RAGState)
        workflow.add_node("contextualize", self._contextualize_question)
        workflow.add_node("retrieve", self._retrieve_documents)
        workflow.add_node("generate", self._generate_answer)
        workflow.add_edge(START, "contextualize")
        workflow.add_edge("contextualize", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        self.graph = workflow.compile()

    def _contextualize_question(self, state: RAGState) -> dict[str, str]:
        chat_history = state.get("chat_history", [])
        question = state["input"]
        if not chat_history:
            return {"standalone_question": question}

        messages = self.contextualize_prompt.format_messages(chat_history=chat_history, input=question)
        response = self.llm.invoke(messages)
        standalone_question = getattr(response, "content", str(response)).strip()
        return {"standalone_question": standalone_question or question}

    def _retrieve_documents(self, state: RAGState) -> dict[str, list[Document]]:
        question = state.get("standalone_question") or state["input"]
        documents_with_scores = self.vector_store.similarity_search_with_score(question, k=settings.top_k)
        documents = [
            Document(
                page_content=document.page_content,
                metadata={**document.metadata, "score": float(score)},
            )
            for document, score in documents_with_scores
        ]
        return {"context": documents}

    def _generate_answer(self, state: RAGState) -> dict[str, str]:
        context_documents = state.get("context", [])
        question = state.get("standalone_question") or state["input"]
        context_text = "\n\n".join(document.page_content for document in context_documents)
        messages = self.answer_prompt.format_messages(
            chat_history=state.get("chat_history", []),
            input=question,
            context=context_text,
        )
        response = self.llm.invoke(messages)
        answer = getattr(response, "content", str(response)).strip()
        return {"answer": answer}

    def answer(self, question: str, chat_history):
        return self.graph.invoke({"input": question, "chat_history": chat_history})
