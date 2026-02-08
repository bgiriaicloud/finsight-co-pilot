"""
Gemini API Client wrapper for the Financial Analyst Co-Pilot.
Uses google-generativeai SDK with API key from environment.
"""

import os
import io
import time
import tempfile
import google.generativeai as genai


# Maximum characters of extracted PDF text to send as a prompt fallback.
_MAX_TEXT_CHARS = 60_000


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from a PDF using PyPDF2 (local, no API call)."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- Page {i + 1} ---\n{text}")
        return "\n\n".join(pages)
    except Exception:
        return ""


class GeminiClient:
    """Singleton wrapper around Google's Generative AI (Gemini) API."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "No Gemini API key found. "
                "Set GEMINI_API_KEY or GOOGLE_API_KEY in your .env file."
            )
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    # ── internal retry helper ───────────────────────────────────────────
    def _call_with_retry(self, fn, max_retries: int = 4):
        """Call *fn()* with exponential back-off on 429 / 503 errors."""
        last_err = None
        for attempt in range(max_retries):
            try:
                return fn()
            except Exception as e:
                last_err = e
                err_str = str(e)
                # Retry only on rate-limit (429) or temporary server errors
                if "429" in err_str or "503" in err_str or "Resource exhausted" in err_str:
                    wait = 2 ** attempt + 1          # 2, 3, 5, 9 seconds
                    time.sleep(wait)
                else:
                    raise
        raise last_err  # type: ignore[misc]

    # ── text generation ─────────────────────────────────────────────────
    def generate(
        self,
        prompt: str,
        system_instruction: str = None,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Generate text from a prompt using Gemini."""
        try:
            model = self.model
            if system_instruction:
                model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    system_instruction=system_instruction,
                )

            def _call():
                return model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                )

            response = self._call_with_retry(_call)
            return response.text
        except Exception as e:
            return f"Error generating response: {str(e)}"

    # ── document / PDF analysis ─────────────────────────────────────────
    def analyze_document(
        self,
        file_bytes: bytes,
        query: str,
        filename: str = "document.pdf",
    ) -> str:
        """Analyse an uploaded document.

        Strategy:
        1. Try the Gemini File-Upload multimodal API (best quality).
        2. On rate-limit (429) after retries, fall back to local text
           extraction with PyPDF2 and send the text as a normal prompt.
        """
        # ---- attempt 1: multimodal upload ----
        tmp_path = None
        try:
            suffix = os.path.splitext(filename)[1] or ".pdf"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            def _upload_and_generate():
                uploaded_file = genai.upload_file(tmp_path, display_name=filename)
                # Wait for server-side processing
                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(1)
                    uploaded_file = genai.get_file(uploaded_file.name)
                if uploaded_file.state.name == "FAILED":
                    raise RuntimeError("Document processing failed on server.")
                return self.model.generate_content(
                    [uploaded_file, query],
                    generation_config=genai.GenerationConfig(
                        temperature=0.2,
                        max_output_tokens=8192,
                    ),
                )

            response = self._call_with_retry(_upload_and_generate)
            return response.text

        except Exception as upload_err:
            # ---- attempt 2: text-based fallback ----
            pdf_text = _extract_pdf_text(file_bytes)
            if not pdf_text:
                return (
                    f"Error analyzing document: {upload_err}\n\n"
                    "Additionally, could not extract text from the PDF for a "
                    "fallback analysis.  Please try again in a minute."
                )

            # Truncate to stay within context limits
            if len(pdf_text) > _MAX_TEXT_CHARS:
                pdf_text = pdf_text[:_MAX_TEXT_CHARS] + "\n\n... [text truncated] ..."

            fallback_prompt = (
                f"The following is the extracted text of a financial document "
                f"named '{filename}'.\n\n"
                f"DOCUMENT TEXT:\n{pdf_text}\n\n"
                f"QUESTION / TASK:\n{query}"
            )
            return self.generate(
                fallback_prompt,
                system_instruction=(
                    "You are an expert financial document analyst. "
                    "Analyse the document text provided and answer the question thoroughly."
                ),
                temperature=0.2,
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # ── multi-turn chat ─────────────────────────────────────────────────
    def chat_completion(self, messages: list, system_instruction: str = None) -> str:
        """Multi-turn chat completion."""
        try:
            model = self.model
            if system_instruction:
                model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    system_instruction=system_instruction,
                )

            chat = model.start_chat(history=[])
            for msg in messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                chat.history.append(
                    genai.types.content_types.ContentDict(
                        role=role, parts=[msg["content"]]
                    )
                )

            last_msg = messages[-1]["content"]

            def _call():
                return chat.send_message(
                    last_msg,
                    generation_config=genai.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=8192,
                    ),
                )

            response = self._call_with_retry(_call)
            return response.text
        except Exception as e:
            return f"Error in chat: {str(e)}"
