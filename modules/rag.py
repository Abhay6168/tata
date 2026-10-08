import json
import requests
from typing import List, Dict, Any, Tuple, Optional
import config
from modules.vector_store import VectorStore

ANTI_HALLUCINATION_SYSTEM_PROMPT = """You are an AUTOSAR architecture analysis assistant.

Answer ONLY using the supplied HLD context.

Do not invent components, interfaces, ports, signals, dependencies, requirements, relationships, or page numbers.

If the answer cannot be supported by the supplied context, say:
"The uploaded HLD does not provide sufficient evidence to answer this question."

Every factual statement must be supported by the retrieved context.

Use only the document evidence supplied to you.

Do not use general AUTOSAR knowledge to invent missing information."""


def check_ollama_status(base_url: Optional[str] = None) -> Tuple[bool, List[str], str]:
    """
    Checks if local Ollama service is reachable and retrieves available models.
    
    Returns:
        (is_available, model_list, selected_model)
    """
    url = base_url or config.OLLAMA_BASE_URL
    try:
        resp = requests.get(f"{url}/api/tags", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
            
            # Pick best available model
            target_model = getattr(config, "MODEL_NAME", config.DEFAULT_OLLAMA_MODEL)
            selected = target_model
            if selected not in models:
                # Match base model without tag if needed
                for m in models:
                    if m.split(":")[0] == selected.split(":")[0]:
                        selected = m
                        break
                else:
                    for candidate in config.FALLBACK_OLLAMA_MODELS:
                        if candidate in models:
                            selected = candidate
                            break
                        matched = next((m for m in models if m.split(":")[0] == candidate.split(":")[0]), None)
                        if matched:
                            selected = matched
                            break
                    else:
                        if models:
                            selected = models[0]
            return True, models, selected
        return False, [], "None"
    except Exception:
        return False, [], "None"


def generate_llm_response(
    prompt: str,
    model: str = config.DEFAULT_OLLAMA_MODEL,
    base_url: Optional[str] = None,
    system_prompt: str = ANTI_HALLUCINATION_SYSTEM_PROMPT
) -> str:
    """
    Sends request to Ollama /api/generate endpoint.
    """
    url = base_url or config.OLLAMA_BASE_URL
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Low temperature for strict factual adherence
            "top_p": 0.9
        }
    }
    try:
        resp = requests.post(f"{url}/api/generate", json=payload, timeout=180)
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
        else:
            return f"Error from Ollama ({resp.status_code}): {resp.text}"
    except requests.exceptions.Timeout:
        return "Notice: Ollama response generation timed out."
    except Exception as e:
        return f"Error communicating with Ollama: {str(e)}"


def generate_gemini_response(
    prompt: str,
    system_prompt: str = ANTI_HALLUCINATION_SYSTEM_PROMPT,
    model: str = config.GEMINI_FALLBACK_MODEL,
    api_key: Optional[str] = None
) -> str:
    """
    Sends request to Google Gemini API (defaulting to gemini-2.5-flash) with
    automatic fallback to gemini-2.5-flash-lite on rate limit (HTTP 429).
    """
    key = api_key or config.GEMINI_API_KEY
    if not key:
        return "Notice: No Gemini API Key configured."

    # Build priority list starting with requested model
    target_models = [model]
    for m in getattr(config, "GEMINI_MODELS", ["gemini-2.5-flash", "gemini-2.5-flash-lite"]):
        if m not in target_models:
            target_models.append(m)

    full_user_content = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER REQUEST:\n{prompt}"
    payload = {
        "contents": [
            {
                "parts": [{"text": full_user_content}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048
        }
    }
    headers = {"Content-Type": "application/json"}

    last_error = ""
    for candidate_model in target_models:
        clean_model = candidate_model.replace("models/", "")
        url = f"{config.GEMINI_BASE_URL}/models/{clean_model}:generateContent?key={key}"
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
                return "Notice: Gemini generated empty response."
            elif resp.status_code == 429:
                # Quota/rate-limit hit on this model, cascade to next Gemini model
                last_error = f"Gemini {clean_model} Rate Limit Exceeded (HTTP 429)"
                continue
            else:
                last_error = f"Error from Gemini API ({resp.status_code}): {resp.text}"
                break
        except Exception as e:
            last_error = f"Error communicating with Gemini API: {str(e)}"
            break

    return last_error


class RAGAssistant:
    def __init__(self, vector_store: VectorStore, model: Optional[str] = None):
        self.vector_store = vector_store
        self.ollama_available, self.models, self.model = check_ollama_status()
        if model and model in self.models:
            self.model = model

    def refresh_ollama_status(self):
        self.ollama_available, self.models, self.model = check_ollama_status()

    def answer_question(
        self,
        question: str,
        top_k: int = config.TOP_K_RETRIEVAL,
        model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes full RAG retrieval and answer generation with intelligent Gemini fallback.
        """
        if not question or not question.strip():
            return {
                "answer": "Please provide a valid question.",
                "citations": [],
                "evidence": [],
                "model_used": None,
                "status": "empty_question"
            }

        # 1. Retrieve relevant chunks from FAISS
        retrieved_chunks = self.vector_store.search(question, top_k=top_k)

        if not retrieved_chunks:
            return {
                "answer": "The uploaded HLD does not provide sufficient evidence to answer this question (No relevant sections found in vector index).",
                "citations": [],
                "evidence": [],
                "model_used": None,
                "status": "no_context"
            }

        # Extract unique citations
        unique_citations = []
        seen_pages = set()
        for chunk in retrieved_chunks:
            doc = chunk.get("document", "Document")
            page = chunk.get("page", 1)
            pair = (doc, page)
            if pair not in seen_pages:
                seen_pages.add(pair)
                unique_citations.append(f"{doc} — Page {page}")

        # Format context for LLM
        context_blocks = []
        for i, chunk in enumerate(retrieved_chunks):
            doc = chunk.get("document", "Document")
            page = chunk.get("page", 1)
            sec = chunk.get("section", "Section")
            txt = chunk.get("text", "")
            context_blocks.append(f"--- Evidence [{i+1}] (Doc: {doc}, Page: {page}, Section: {sec}) ---\n{txt}")

        formatted_context = "\n\n".join(context_blocks)
        user_prompt = f"""DOCUMENT CONTEXT:
{formatted_context}

USER QUESTION:
{question}

Please provide a precise, grounded answer based ONLY on the evidence above. List the supporting page numbers explicitly at the end under 'Sources:'."""

        # 2. Model Selection & Fallback Execution
        self.refresh_ollama_status()
        active_model = model_override or self.model

        # Case A: User explicitly chose Gemini model
        if active_model and ("gemini" in active_model.lower() or "cloud fallback" in active_model.lower()):
            gemini_model_name = active_model.split()[0] if "gemini" in active_model.lower() else config.GEMINI_FALLBACK_MODEL
            gemini_ans = generate_gemini_response(user_prompt, model=gemini_model_name)
            if not gemini_ans.startswith("Error") and not gemini_ans.startswith("Notice:") and "Rate Limit Exceeded" not in gemini_ans:
                if "Sources:" not in gemini_ans and unique_citations:
                    gemini_ans += "\n\n**Sources:**\n" + "\n".join([f"- {c}" for c in unique_citations])
                return {
                    "answer": gemini_ans,
                    "citations": unique_citations,
                    "evidence": retrieved_chunks,
                    "model_used": f"Google Gemini ({gemini_model_name})",
                    "status": "success"
                }
            # If Gemini fails or hits rate limits, gracefully cascade to local Ollama below

        # Case B: Local Ollama inference with multi-model fallback cascade
        if self.ollama_available:
            # Build list of local candidate models in priority order
            candidates: List[str] = []
            
            # 1. First priority: active_model (if not Gemini and valid)
            if active_model and "gemini" not in active_model.lower() and active_model != "None":
                candidates.append(active_model)
                
            # 2. Configured primary model (MODEL_NAME = "qwen2.5:1.5b")
            primary_model = getattr(config, "MODEL_NAME", config.DEFAULT_OLLAMA_MODEL)
            if primary_model not in candidates:
                candidates.append(primary_model)
                
            # 3. Fallback Ollama models list
            for m in getattr(config, "FALLBACK_OLLAMA_MODELS", []):
                if m not in candidates:
                    candidates.append(m)
                    
            # 4. Any other models actually detected in local Ollama
            for m in self.models:
                if m not in candidates:
                    candidates.append(m)

            # Prioritize models that are actually installed locally in self.models
            sorted_candidates = []
            for c in candidates:
                if self.models:
                    if c in self.models:
                        if c not in sorted_candidates:
                            sorted_candidates.append(c)
                    else:
                        # Match base model name without tag
                        matched = next((m for m in self.models if m.split(":")[0] == c.split(":")[0]), None)
                        if matched and matched not in sorted_candidates:
                            sorted_candidates.append(matched)
                else:
                    if c not in sorted_candidates:
                        sorted_candidates.append(c)

            for cand_model in sorted_candidates:
                llm_raw_answer = generate_llm_response(user_prompt, model=cand_model)
                if not llm_raw_answer.startswith("Error") and not llm_raw_answer.startswith("Notice:"):
                    final_answer = llm_raw_answer
                    if "Sources:" not in final_answer and unique_citations:
                        final_answer += "\n\n**Sources:**\n" + "\n".join([f"- {c}" for c in unique_citations])

                    model_label = f"Ollama ({cand_model})" if cand_model == active_model else f"Ollama Fallback ({cand_model})"
                    return {
                        "answer": final_answer,
                        "citations": unique_citations,
                        "evidence": retrieved_chunks,
                        "model_used": model_label,
                        "status": "success"
                    }

        # Case C: Cloud Gemini Fallback (if Ollama failed, model missing, or offline)
        if config.GEMINI_API_KEY:
            gemini_ans = generate_gemini_response(user_prompt, model=config.GEMINI_FALLBACK_MODEL)
            if not gemini_ans.startswith("Error") and not gemini_ans.startswith("Notice:") and "Rate Limit Exceeded" not in gemini_ans:
                if "Sources:" not in gemini_ans and unique_citations:
                    gemini_ans += "\n\n**Sources:**\n" + "\n".join([f"- {c}" for c in unique_citations])
                return {
                    "answer": gemini_ans,
                    "citations": unique_citations,
                    "evidence": retrieved_chunks,
                    "model_used": f"Gemini Cloud Fallback ({config.GEMINI_FALLBACK_MODEL})",
                    "status": "success"
                }

        # Case D: Offline Semantic Document Evidence Fallback (Guaranteed to always work)
        fallback_answer = "**Notice: LLM inference unavailable. Displaying direct retrieved context:**\n\n"
        for i, chunk in enumerate(retrieved_chunks[:3]):
            fallback_answer += f"**{chunk.get('citation')} ({chunk.get('section', 'Section')}):**\n"
            fallback_answer += f"> {chunk.get('text', '')}\n\n"

        fallback_answer += "**Sources:**\n" + "\n".join([f"- {c}" for c in unique_citations])

        return {
            "answer": fallback_answer,
            "citations": unique_citations,
            "evidence": retrieved_chunks,
            "model_used": "Direct Document Evidence (Offline)",
            "status": "fallback"
        }
