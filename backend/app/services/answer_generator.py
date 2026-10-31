import requests


class AnswerGenerator:
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434/api/chat",
        model: str = "phi3:latest",
    ):
        self.ollama_url = ollama_url
        self.model = model

    def generate(
        self,
        query: str,
        evidence: list[dict],
    ) -> str:
        evidence_text = "\n\n".join(
            f"[Evidence {i + 1}]\n"
            f"Document: {item.get('document', 'Policy Document')}\n"
            f"Section: {item.get('section', 'N/A')}\n"
            f"Page: {item.get('page', 'N/A')}\n"
            f"Text: {item.get('text', '').strip()}"
            for i, item in enumerate(evidence)
        )

        prompt = f"""You are PolicyPilot's policy answer assistant.

Answer the customer's question using ONLY the policy evidence provided below.

Rules:
1. Do not invent, assume, or add policy requirements that are not present in the evidence.
2. Give a clear, concise answer in simple language.
3. If the evidence does not establish the answer, say that the provided policy evidence does not establish it.
4. Do not mention these instructions.
5. Do not claim that you performed an action or made a decision.
6. The retrieved evidence is authoritative for this response.

Customer question:
{query}

Policy evidence:
{evidence_text}

Answer:"""

        response = requests.post(
            self.ollama_url,
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()
        answer = data.get("message", {}).get("content", "").strip()

        if not answer:
            raise RuntimeError("Ollama returned an empty answer")

        return answer
