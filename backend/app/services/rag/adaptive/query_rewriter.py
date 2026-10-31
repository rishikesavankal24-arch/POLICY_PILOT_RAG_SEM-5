import re


class QueryRewriter:
    """
    Deterministic, meaning-preserving query reformulator for policy retrieval.

    The rewriter removes grammatical question scaffolding while preserving:
    - policy concepts
    - information requirements
    - numbers and units
    - conditions and qualifiers
    - important multi-word terms

    It does not add policy-specific facts.
    """

    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "being",
        "by",
        "can",
        "could",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "its",
        "may",
        "of",
        "on",
        "or",
        "should",
        "the",
        "their",
        "these",
        "this",
        "those",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "would",
    }

    QUESTION_REPLACEMENTS = (
        # Definition questions
        (
            r"^\s*what\s+is\s+the\s+meaning\s+of\s+",
            "definition ",
        ),
        (
            r"^\s*what\s+is\s+the\s+definition\s+of\s+",
            "definition ",
        ),
        (
            r"^\s*what\s+does\s+(.+?)\s+mean\s+",
            r"definition \1 ",
        ),

        # Threshold questions
        (
            r"^\s*what\s+is\s+the\s+threshold\s+for\s+",
            "threshold ",
        ),

        # Purpose / objective questions
        (
            r"^\s*what\s+are\s+the\s+objectives\s+and\s+purpose\s+of\s+",
            "objectives purpose ",
        ),
        (
            r"^\s*what\s+is\s+the\s+purpose\s+of\s+",
            "purpose ",
        ),

        # Provision questions
        (
            r"^\s*what\s+are\s+the\s+provisions\s+relating\s+to\s+",
            "provisions ",
        ),
        (
            r"^\s*what\s+are\s+the\s+provisions\s+related\s+to\s+",
            "provisions ",
        ),

        # Coverage questions
        (
            r"^\s*which\s+entities\s+are\s+covered\s+by\s+",
            "covered entities ",
        ),
    )

    def rewrite(self, query: str) -> str:
        if not isinstance(query, str):
            raise TypeError("query must be a string")

        query = query.strip()

        if not query:
            raise ValueError("query must not be empty")

        query = self._normalize(query)
        query = self._apply_question_replacements(query)
        query = self._remove_question_scaffolding(query)
        query = self._deduplicate_tokens(query)
        query = self._normalize_spacing(query)

        if not query:
            raise ValueError("query produced an empty rewrite")

        return query

    @staticmethod
    def _normalize(query: str) -> str:
        """Normalize case and punctuation while preserving useful symbols."""
        query = query.lower()

        # Preserve:
        # - hyphens: paid-up
        # - percentages: 10%
        # - currency/value symbols
        # - decimal points
        query = re.sub(r"[^\w\s%₹$€£./-]", " ", query)

        query = re.sub(r"\s+", " ", query)

        return query.strip()

    def _apply_question_replacements(self, query: str) -> str:
        """
        Replace only generic question structures.

        These replacements preserve the user's information requirement.
        """
        for pattern, replacement in self.QUESTION_REPLACEMENTS:
            rewritten = re.sub(
                pattern,
                replacement,
                query,
                flags=re.IGNORECASE,
            )

            if rewritten != query:
                query = rewritten
                break

        return query.strip()

    def _remove_question_scaffolding(self, query: str) -> str:
        """
        Remove low-information grammatical words.

        Important semantic terms such as:
        threshold, purpose, objectives, definition, percentage,
        covered, required, penalty, provisions, etc.
        remain available to retrieval.
        """
        tokens = query.split()
        kept = []

        for token in tokens:
            token = token.strip(".,;:!?")

            if not token:
                continue

            # Preserve all numeric/value-bearing tokens.
            if self._contains_value_signal(token):
                kept.append(token)
                continue

            if token not in self.STOP_WORDS:
                kept.append(token)

        return " ".join(kept)

    @staticmethod
    def _contains_value_signal(token: str) -> bool:
        """Preserve numbers, percentages, currencies and common units."""
        if re.search(r"\d", token):
            return True

        return token in {
            "rupees",
            "rupee",
            "percent",
            "percentage",
            "crore",
            "crores",
            "lakh",
            "lakhs",
            "million",
            "billion",
            "thousand",
            "years",
            "year",
            "months",
            "month",
            "days",
            "day",
            "hours",
            "hour",
        }

    @staticmethod
    def _deduplicate_tokens(query: str) -> str:
        """Remove exact duplicate tokens while preserving their order."""
        seen = set()
        result = []

        for token in query.split():
            if token not in seen:
                seen.add(token)
                result.append(token)

        return " ".join(result)

    @staticmethod
    def _normalize_spacing(query: str) -> str:
        return re.sub(r"\s+", " ", query).strip()
