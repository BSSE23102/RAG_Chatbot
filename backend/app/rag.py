from __future__ import annotations

from typing import TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import END, START, StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import settings


SYSTEM_PROMPT = (
    "You are a helpful assistant for the NetSol Technologies website. "
    "Answer questions strictly based on the supplied context about NetSol's products, "
    "services, and company information. "
    "If the context does not contain enough information to answer the question, "
    "say that you do not have information on that topic."
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
        if not settings.google_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set. Add it to backend/.env before starting the app.")

        self.llm = ChatGoogleGenerativeAI(model=settings.chat_model, google_api_key=settings.google_api_key, temperature=0.2)
        self.contextualize_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "human",
                    "Given the following conversation history and a follow-up question, rewrite the follow-up question to be a standalone question (i.e. self-contained and search-friendly). "
                    "Do NOT answer the question, do NOT add any conversational introduction, just output the rewritten standalone question.\n\n"
                    "Conversation History:\n"
                    "{chat_history}\n\n"
                    "Follow-up Question: {input}\n\n"
                    "Standalone Question:"
                )
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

        formatted_history = "\n".join(
            f"{'Human' if msg.type == 'human' else 'Assistant'}: {msg.content}"
            for msg in chat_history
        )
        messages = self.contextualize_prompt.format_messages(chat_history=formatted_history, input=question)
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
