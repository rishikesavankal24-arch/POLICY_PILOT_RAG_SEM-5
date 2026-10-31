import re


class EvidenceEvaluator:
    """Deterministically evaluate whether retrieved policy evidence is answer-bearing.

    The evaluator is intentionally retrieval-only: it does not decide whether a
    loan is compliant, eligible, approved, or rejected. It only decides whether
    the retrieved policy text contains enough evidence to answer the user's
    information need and whether that evidence is traceable.
    """

    # Words that mostly express the question rather than its policy topic.
    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
        "can", "could", "did", "do", "does", "for", "from", "how", "if",
        "in", "is", "it", "its", "may", "of", "on", "or", "should", "the",
        "their", "these", "this", "those", "to", "was", "were", "what",
        "when", "which", "who", "why", "with", "would", "that", "than",
        "then", "them", "under", "into", "about", "apply", "applies", "applied",
        "applicable", "relating", "related", "following", "mean", "meaning",
        "means", "defined", "definition", "purpose", "purposes", "objective",
        "objectives", "aim", "threshold", "limit", "maximum", "minimum", "amount",
        "percentage", "percent", "penalty", "penalties", "fine", "fines",
        "punishment", "punishable", "prosecution", "imprisonment", "provision",
        "provisions", "restriction", "restrictions", "requirement",
        "requirements", "rule", "rules", "procedure", "process", "steps",
        "effective", "commencement", "date", "period", "deadline", "sanctioned",
        "sanctioning", "reported", "reporting", "report", "file", "filing",
        "granted", "granting", "qualifies", "happen", "following", "doesn",
        "isn", "what", "there", "here",
    }

    # Query-side answer requirements.
    INTENT_MARKERS = {
        "definition": (
            "meaning",
            "define",
            "definition",
            "what does",
            "what is meant by",
        ),
        "threshold": (
            "threshold",
            "limit",
            "maximum",
            "minimum",
            "amount",
            "percentage",
            "percent",
            "how much",
            "how many",
            "rupees",
            "crore",
            "lakh",
        ),
        "purpose": (
            "purpose",
            "purposes",
            "objective",
            "objectives",
            "aim",
            "why",
        ),
        "coverage": (
            "covered",
            "coverage",
            "entities",
            "applicable",
            "applies to",
            "who is covered",
            "who are covered",
            "which entities",
        ),
        "penalty": (
            "penalty",
            "penalties",
            "fine",
            "fines",
            "punish",
            "punishment",
            "punishable",
            "prosecution",
            "imprisonment",
            "criminal penalty",
        ),
        "timing": (
            "when is",
            "when are",
            "when was",
            "when were",
            "when required",
            "effective",
            "commencement",
            "deadline",
            "how long",
            "within",
        ),
        "procedure": (
            "procedure",
            "process",
            "steps",
            "how to",
            "how do",
            "report",
            "reported",
            "reporting",
            "file",
            "filing",
            "sanctioned",
            "sanctioning",
        ),
        "document_requirement": (
            "document",
            "documents",
            "paperwork",
            "documentation",
            "required document",
            "required documents",
            "documents required",
            "what documents",
            "which documents",
            "documents needed",
            "what paperwork",
            "which paperwork",
            "what do i need to submit",
            "what do i need to provide",
            "what needs to be submitted",
            "what needs to be provided",
            "which documents must be submitted",
            "which documents must be provided",
        ),
        "rule": (
            "provisions",
            "provision",
            "restriction",
            "restrictions",
            "requirement",
            "requirements",
            "rules",
            "rule",
            "should",
            "must",
            "shall",
        ),
    }

    # Evidence-side markers.
    EVIDENCE_PATTERNS = {
        "definition": (
            re.compile(
                r"\bshall\s+(?:have\s+)?the\s+meaning\s+assigned\s+to\s+it\b",
                re.I,
            ),
            re.compile(r"\bshall\s+mean\b", re.I),
            re.compile(r"\bmeans?\b", re.I),
            re.compile(r"\bdefined\s+(?:as|to mean)\b", re.I),
            re.compile(r"\brefers?\s+to\b", re.I),
            re.compile(r"\bis\s+(?:a|an|the)\b", re.I),
            re.compile(
                r"\bcomprises?\b|\bconsists?\s+of\b|\bintegrates?\b",
                re.I,
            ),
        ),
        "threshold": (
            re.compile(
                r"\b\d+(?:\.\d+)?\s*(?:%|percent)\b",
                re.I,
            ),
            re.compile(
                r"(?:₹|rs\.?|rupees?)\s*[\d,]+(?:\.\d+)?",
                re.I,
            ),
            re.compile(
                r"\b\d+(?:\.\d+)?\s*(?:crore|lakh|million|billion)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:threshold|limit|maximum|minimum)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:equal\s+to|exceeding|above|below|less\s+than|more\s+than)\b",
                re.I,
            ),
        ),
        "purpose": (
            re.compile(r"\bin\s+order\s+to\b", re.I),
            re.compile(
                r"\b(?:purpose|objective|objectives|aim)\s+(?:of|is|are)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:designed|intended)\s+to\b",
                re.I,
            ),
            re.compile(
                r"\bto\s+(?:prevent|ensure|promote|protect|facilitate|improve|combat|maintain)\b",
                re.I,
            ),
            re.compile(
                r"\bin\s+(?:the\s+)?public\s+interest\b",
                re.I,
            ),
        ),
        "coverage": (
            re.compile(
                r"\b(?:covers?|covered|applicable|applies?)\s+(?:the|to|following)?\b",
                re.I,
            ),
            re.compile(
                r"\b(?:shall|will)\s+apply\s+to\b",
                re.I,
            ),
            re.compile(
                r"\b(?:entities|banks|companies|institutions)\s+(?:covered|covered\s+by)\b",
                re.I,
            ),
            re.compile(r"\b(?:includes?|including)\b", re.I),
        ),
        "penalty": (
            re.compile(
                r"\bpenalt(?:y|ies)\s+(?:of|up\s+to|may|shall|will|applies?|apply)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:liable|liable\s+to)\b.{0,100}\b(?:fine|penalty|imprisonment|prosecution|punish)",
                re.I | re.S,
            ),
            re.compile(
                r"\b(?:fine|fines)\s+(?:of|up\s+to)\b",
                re.I,
            ),
            re.compile(
                r"\bpunishable\s+(?:with|by)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:imprisonment|prosecution)\b",
                re.I,
            ),
            re.compile(
                r"\bcriminal\s+(?:offen[cs]e|liability|proceedings?|action)\b",
                re.I,
            ),
        ),
        "timing": (
            re.compile(
                r"\b(?:effective|with\s+effect)\s+(?:from|on)\b",
                re.I,
            ),
            re.compile(r"\bcommencement\b", re.I),
            re.compile(
                r"\bwithin\s+\w+(?:\s+\w+)?\b",
                re.I,
            ),
            re.compile(
                r"\b(?:before|after|prior\s+to|subsequent\s+to)\b",
                re.I,
            ),
            re.compile(
                r"\bat\s+the\s+time\s+of\b",
                re.I,
            ),
            re.compile(
                r"\b(?:days?|hours?|months?|years?)\b",
                re.I,
            ),
        ),
        "procedure": (
            re.compile(
                r"\b(?:procedure|process|steps?)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:shall|should|must)\s+(?:report|submit|file|record|notify|sanction|obtain|verify|identify)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:reported|reporting|filing|sanctioned|sanctioning)\b",
                re.I,
            ),
            re.compile(
                r"\bsubmit(?:ted)?\b|\bnotify\b|\brecord(?:ed)?\b",
                re.I,
            ),
        ),
        "document_requirement": (
            re.compile(
                r"\b(?:must|shall|should)\s+(?:provide|submit|produce|furnish|present|attach|upload|include|contain)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:required|required\s+to)\s+(?:provide|submit|produce|furnish|present|attach|upload|include|contain)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:required|mandatory|necessary)\s+documents?\b",
                re.I,
            ),
            re.compile(
                r"\bdocuments?\s+(?:must|shall|should)\s+be\s+(?:provided|submitted|produced|furnished|presented|attached|uploaded|included|contained)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:submit|provide|produce|furnish|present|attach|upload|include|contain)\b.{0,100}"
                r"\b(?:document|documents|certificate|certificates|"
                r"record|records|statement|statements|proof|"
                r"license|licence|registration|insurance|policy|"
                r"deed|agreement|identity|identification)\b",
                re.I | re.S,
            ),
            re.compile(
                r"\b(?:document|documents|certificate|certificates|"
                r"record|records|statement|statements|proof|"
                r"license|licence|registration|insurance|policy|"
                r"deed|agreement|identity|identification)\b.{0,100}"
                r"\b(?:required|mandatory|necessary)\b",
                re.I | re.S,
            ),
        ),
        "rule": (
            re.compile(
                r"\b(?:shall|must|should)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:provision|provisions|restriction|restrictions|requirement|requirements)\b",
                re.I,
            ),
            re.compile(
                r"\b(?:prohibited|permitted|not\s+be|may\s+be)\b",
                re.I,
            ),
            re.compile(
                r"\bresponsibilit(?:y|ies)\b.{0,100}\bvests?\b",
                re.I,
            ),
        ),
    }

    # Query terms that identify an answer type rather than the policy subject.
    INTENT_WORDS = {
        word
        for markers in INTENT_MARKERS.values()
        for marker in markers
        for word in re.findall(
            r"[a-z0-9]+",
            marker.lower(),
        )
    }

    DOCUMENT_INTENT_WORDS = {
        "document",
        "documents",
        "paperwork",
        "documentation",
        "required",
        "requirements",
        "requirement",
        "needed",
        "need",
        "submit",
        "submitted",
        "provide",
        "provided",
        "produce",
        "produced",
        "furnish",
        "furnished",
        "present",
        "presented",
        "attach",
        "attached",
        "upload",
        "uploaded",
        "include",
        "included",
        "contain",
        "contains",
        "mandatory",
        "necessary",
    }

    INTENT_WORDS.update(DOCUMENT_INTENT_WORDS)

    def evaluate(
        self,
        query: str,
        retrieval_result: dict,
    ) -> dict:
        """Return a conservative, explainable sufficiency decision."""
        self._validate_inputs(query, retrieval_result)

        results = retrieval_result["results"]

        if not results:
            return self._empty_result(
                "No policy evidence was retrieved."
            )

        valid_results = [
            result
            for result in results
            if isinstance(result, dict)
        ]

        if not valid_results:
            return self._empty_result(
                "No valid retrieved evidence records were found.",
                len(results),
            )

        intents = self._detect_intents(query)

        substantive_results = [
            result
            for result in valid_results
            if self._is_substantive(
                result,
                intents=intents,
            )
        ]

        provenance_results = [
            result
            for result in valid_results
            if self._has_provenance(result)
        ]

        # A result is allowed to establish answer coverage only when it is
        # BOTH substantive and traceable.
        traceable_substantive_results = [
            result
            for result in substantive_results
            if self._has_provenance(result)
        ]

        query_terms = self._extract_terms(query)

        topic_terms = [
            term
            for term in query_terms
            if term not in self.INTENT_WORDS
        ]

        evidence_text = "\n".join(
            result["text"]
            for result in traceable_substantive_results
        )

        normalized_evidence = self._normalize(
            evidence_text
        )

        matched_terms = [
            term
            for term in topic_terms
            if self._contains_term(
                normalized_evidence,
                term,
            )
        ]

        term_coverage = (
            len(matched_terms) / len(topic_terms)
            if topic_terms
            else 1.0
        )

        covered_requirements = []
        missing_requirements = []
        requirement_details = []

        for intent in intents:
            matches = self._find_requirement_support(
                intent,
                traceable_substantive_results,
                topic_terms,
            )

            supporting_chunk_ids = [
                result.get("chunk_id", "")
                for result in matches
                if isinstance(
                    result.get("chunk_id"),
                    str,
                )
                and result.get("chunk_id").strip()
            ]

            supported = bool(matches)

            requirement_details.append(
                {
                    "type": intent,
                    "supported": supported,
                    "supporting_chunk_ids": supporting_chunk_ids,
                }
            )

            if supported:
                covered_requirements.append(intent)
            else:
                missing_requirements.append(intent)

        topic_coverage_ok = (
            self._topic_coverage_is_sufficient(
                topic_terms,
                term_coverage,
            )
        )

        # A document-requirement question is allowed to have no explicit
        # topic term, e.g. "What documents are required?".
        if (
            "document_requirement" in covered_requirements
            and not topic_terms
        ):
            topic_coverage_ok = True

        # Definitions are allowed a slightly weaker topical match because
        # definitional questions often contain little topic vocabulary.
        if (
            not topic_coverage_ok
            and "definition" in covered_requirements
            and term_coverage >= 0.33
        ):
            topic_coverage_ok = True

        has_substantive = bool(
            substantive_results
        )

        has_provenance = bool(
            provenance_results
        )

        has_traceable_substantive = bool(
            traceable_substantive_results
        )

        has_answer_requirements = not missing_requirements

        sufficient = (
            has_traceable_substantive
            and topic_coverage_ok
            and has_answer_requirements
        )

        reasons = []

        if not has_substantive:
            reasons.append(
                "no substantive policy text"
            )

        if not has_provenance:
            reasons.append(
                "no traceable provenance"
            )

        if not has_traceable_substantive:
            if has_substantive and has_provenance:
                reasons.append(
                    "no single result contains both substantive "
                    "policy text and traceable provenance"
                )
            elif has_substantive:
                reasons.append(
                    "substantive policy text is not traceable"
                )
            elif has_provenance:
                reasons.append(
                    "traceable results do not contain substantive "
                    "policy text"
                )

        if not topic_coverage_ok:
            reasons.append(
                "low topical coverage"
            )

        if missing_requirements:
            reasons.append(
                "missing answer requirements: "
                + ", ".join(missing_requirements)
            )

        if sufficient:
            reason = (
                "Retrieved evidence covers the requested information "
                "requirements, has adequate topical alignment, contains "
                "substantive policy text, and has traceable provenance."
            )

            status = "sufficient"

        else:
            reason = (
                "Retrieved evidence is insufficient"
            )

            if reasons:
                reason += ": " + "; ".join(reasons)

            reason += "."
            status = "insufficient"

        return {
            "evidence_status": status,
            "reason": reason,
            "matched_terms": matched_terms,
            "covered_requirements": covered_requirements,
            "missing_requirements": missing_requirements,
            "requirement_details": requirement_details,
            "evaluated_results": len(results),
            "substantive_results": len(substantive_results),
            "provenance_results": len(provenance_results),
            "term_coverage": round(
                term_coverage,
                3,
            ),
            "concept_density": round(
                self._best_concept_density(
                    topic_terms,
                    traceable_substantive_results,
                ),
                3,
            ),
        }

    def _validate_inputs(
        self,
        query: str,
        retrieval_result: dict,
    ) -> None:
        if not isinstance(query, str):
            raise TypeError(
                "query must be a string"
            )

        if not query.strip():
            raise ValueError(
                "query must not be empty"
            )

        if not isinstance(
            retrieval_result,
            dict,
        ):
            raise TypeError(
                "retrieval_result must be a dictionary"
            )

        if "results" not in retrieval_result:
            raise ValueError(
                "retrieval_result must contain a results list"
            )

        if not isinstance(
            retrieval_result["results"],
            list,
        ):
            raise ValueError(
                "retrieval_result must contain a results list"
            )

    def _detect_intents(
        self,
        query: str,
    ) -> list[str]:
        q = self._normalize(query)

        # Document-identification questions such as
        # "What is the circular related to ...?" ask for the
        # applicable policy/document rather than a definition.
        document_identification = re.search(
            r"\b(?:circular|guideline|policy|notification|direction|scheme)\b"
            r"\s+"
            r"(?:related\s+to|about|for|regarding|concerning|applicable\s+to)\b",
            q,
        )

        # Legal phrasing such as "for the purposes of this circular"
        # is not a request for the policy objective.
        q = re.sub(
            r"\bfor\s+the\s+purpose(?:s)?\s+of\b",
            "",
            q,
        )

        intents = []

        def add(intent: str) -> None:
            if intent not in intents:
                intents.append(intent)

        # Definition / description.
        if (
            re.search(
                r"\b(?:meaning|define|definition|what\s+does|"
                r"what\s+is\s+meant\s+by)\b",
                q,
            )
            or (
                re.search(
                    r"\bwhat\s+is\b",
                    q,
                )
                and not re.search(
                    r"\b(?:threshold|limit|maximum|minimum|amount|"
                    r"percentage|percent|purpose|objective|aim|coverage|"
                    r"procedure|process|rule|rules|provision|provisions|"
                    r"restriction|restrictions|requirement|requirements|"
                    r"required|documents?|paperwork|"
                    r"penalt(?:y|ies)|fine|fines|deadline|date|period)\b",
                    q,
                )
            )
        ):
            add("definition")

        # Threshold / quantitative requirement.
        if re.search(
            r"(?:\b(?:what\s+is|what\s+are|which\s+is|which\s+are)"
            r"\s+(?:the\s+)?(?:threshold|limit|maximum|minimum|amount)\b"
            r"|\b(?:threshold|limit)\s+(?:for|of)\b"
            r"|\bhow\s+much\b"
            r"|\bwhat\s+(?:percentage|percent|amount)\b"
            r"|\b(?:maximum|minimum)\s+(?:amount|limit|threshold)?\b)",
            q,
        ):
            add("threshold")

        if re.search(
            r"\b(?:purpose|objective|objectives|aim|why)\b",
            q,
        ):
            add("purpose")

        if re.search(
            r"(?:\bwhich\s+entities\b"
            r"|\bwho\s+(?:is|are)\s+covered\b"
            r"|\bcovered\s+by\b"
            r"|\bapplicable\s+to\b"
            r"|\bapplies?\s+to\b"
            r"|\bwho\s+is\s+subject\s+to\b)",
            q,
        ):
            add("coverage")

        if re.search(
            r"\b(?:penalt(?:y|ies)|fine|fines|"
            r"punish(?:ment|able)?|prosecution|imprisonment)\b",
            q,
        ):
            add("penalty")

        if re.search(
            r"(?:\bwhen\s+(?:is|are|was|were|required)\b"
            r"|\beffective\b"
            r"|\bcommencement\b"
            r"|\bdeadline\b"
            r"|\bhow\s+long\b"
            r"|\bwithin\b)",
            q,
        ):
            add("timing")

        if re.search(
            r"(?:\bhow\s+(?:to|do|does)\b"
            r"|\bprocedure\b"
            r"|\bprocess\b"
            r"|\bsteps?\b"
            r"|\breport(?:ed|ing)?\b"
            r"|\bfil(?:e|ing)\b"
            r"|\bsanction(?:ed|ing)?)",
            q,
        ):
            add("procedure")

        # Document requirement intent.
        document_requirement = bool(
            re.search(
                r"\b(?:documents?|paperwork|documentation)\b",
                q,
            )
            and re.search(
                r"\b(?:required|required\s+to|needed|need|"
                r"must|shall|should|submit|submitted|provide|"
                r"provided|produce|produced|furnish|furnished|"
                r"present|presented|attach|attached|upload|uploaded|"
                r"mandatory|necessary)\b",
                q,
            )
        )

        document_question = bool(
            re.search(
                r"\b(?:what|which)\s+"
                r"(?:documents?|paperwork|documentation)\b",
                q,
            )
            or re.search(
                r"\bwhat\s+do\s+i\s+need\s+to\s+"
                r"(?:submit|provide|produce|furnish|present|attach|upload)\b",
                q,
            )
            or re.search(
                r"\bwhat\s+(?:needs?|is\s+needed)\s+to\s+be\s+"
                r"(?:submitted|provided|produced|furnished|presented|attached|uploaded)\b",
                q,
            )
        )

        if document_requirement or document_question:
            add("document_requirement")

        # Generic rule intent.
        if not document_requirement and not document_question:
            if re.search(
                r"(?:\bprovisions?\b"
                r"|\brestrictions?\b"
                r"|\brequirements?\b"
                r"|\brules?\b"
                r"|\bshould\b"
                r"|\bmust\b"
                r"|\bshall\b)",
                q,
            ):
                add("rule")

        if document_identification:
            intents = [
                intent
                for intent in intents
                if intent != "definition"
            ]

            if "rule" not in intents:
                intents.append("rule")

        return intents or ["rule"]

    def _extract_terms(
        self,
        query: str,
    ) -> list[str]:
        normalized = self._normalize(query)

        words = re.findall(
            r"[a-z0-9]+",
            normalized,
        )

        terms = []

        for word in words:
            if (
                len(word) <= 2
                or word in self.STOP_WORDS
            ):
                continue

            if word.isdigit():
                continue

            terms.append(word)

        return list(
            dict.fromkeys(terms)
        )

    def _find_requirement_support(
        self,
        intent: str,
        substantive_results: list[dict],
        topic_terms: list[str],
    ) -> list[dict]:
        patterns = self.EVIDENCE_PATTERNS[intent]

        matches = []

        for result in substantive_results:
            raw_text = result["text"]
            text = self._normalize(raw_text)

            if not any(
                pattern.search(text)
                for pattern in patterns
            ):
                continue

            if intent == "document_requirement":
                if not self._has_document_requirement_signal(
                    raw_text
                ):
                    continue

                if topic_terms and not self._document_requirement_is_topic_anchored(
                    raw_text,
                    topic_terms,
                ):
                    continue

                matches.append(result)
                continue

            if topic_terms and not self._requirement_is_topic_anchored(
                raw_text,
                patterns,
                topic_terms,
            ):
                continue

            matches.append(result)

        if intent == "threshold":
            matches = [
                result
                for result in matches
                if self._has_quantitative_or_limit_signal(
                    result["text"]
                )
                and self._threshold_is_topic_anchored(
                    result["text"],
                    topic_terms,
                )
            ]

        if intent == "penalty":
            matches = [
                result
                for result in matches
                if self._has_actual_penalty_signal(
                    result["text"]
                )
            ]

        return matches

    def _has_document_requirement_signal(
        self,
        text: str,
    ) -> bool:
        """Return True only when evidence actually describes required documents."""

        normalized = self._normalize(text)

        document_terms = (
            r"document(?:s)?",
            r"paperwork",
            r"documentation",
            r"certificate(?:s)?",
            r"record(?:s)?",
            r"statement(?:s)?",
            r"proof",
            r"license",
            r"licence",
            r"registration",
            r"insurance",
            r"policy",
            r"deed",
            r"agreement",
            r"identity",
            r"identification",
            r"form(?:s)?",
            r"application(?:s)?",
        )

        document_pattern = (
            r"(?:"
            + "|".join(document_terms)
            + r")"
        )

        requirement_pattern = (
            r"(?:"
            r"must\s+(?:be\s+)?(?:provided|submitted|produced|"
            r"furnished|presented|attached|uploaded|include|contain)"
            r"|shall\s+(?:be\s+)?(?:provided|submitted|produced|"
            r"furnished|presented|attached|uploaded|include|contain)"
            r"|should\s+(?:be\s+)?(?:provided|submitted|produced|"
            r"furnished|presented|attached|uploaded|include|contain)"
            r"|required\s+to\s+(?:provide|submit|produce|furnish|"
            r"present|attach|upload|include|contain)"
            r"|(?:required|mandatory|necessary)\s+"
            r"documents?"
            r"|documents?\s+(?:must|shall|should)\s+be\s+"
            r"(?:provided|submitted|produced|furnished|presented|"
            r"attached|uploaded|included|contained)"
            r"|(?:provide|submit|produce|furnish|present|attach|upload|include|contain)"
            r".{0,100}"
            + document_pattern
            + r"|"
            + document_pattern
            + r".{0,100}"
            r"(?:required|mandatory|necessary)"
            r")"
        )

        return bool(
            re.search(
                requirement_pattern,
                normalized,
                re.I | re.S,
            )
        )

    def _document_requirement_is_topic_anchored(
        self,
        text: str,
        topic_terms: list[str],
    ) -> bool:
        """Require document evidence to be connected to the queried subject."""

        sentences = re.split(
            r"(?<=[.!?;])\s+",
            text,
        )

        document_signal = re.compile(
            r"\b(?:document|documents|paperwork|documentation|"
            r"certificate|certificates|record|records|statement|"
            r"statements|proof|license|licence|registration|"
            r"insurance|policy|deed|agreement|identity|"
            r"identification|form|forms)\b",
            re.I,
        )

        requirement_signal = re.compile(
            r"\b(?:must|shall|should|required|mandatory|necessary|"
            r"submit|submitted|provide|provided|produce|produced|"
            r"furnish|furnished|present|presented|attach|attached|"
            r"upload|uploaded|include|included|contain|contains)\b",
            re.I,
        )

        for sentence in sentences:
            normalized = self._normalize(sentence)

            if not document_signal.search(normalized):
                continue

            if not requirement_signal.search(normalized):
                continue

            if any(
                self._contains_term(
                    normalized,
                    term,
                )
                for term in topic_terms
            ):
                return True

        normalized = self._normalize(text)

        return bool(
            document_signal.search(normalized)
            and requirement_signal.search(normalized)
            and any(
                self._contains_term(
                    normalized,
                    term,
                )
                for term in topic_terms
            )
        )

    def _requirement_is_topic_anchored(
        self,
        text: str,
        patterns: tuple[re.Pattern, ...],
        topic_terms: list[str],
    ) -> bool:
        """Require answer-type evidence in a topic-relevant sentence.

        Avoid treating the periods in a.m. and p.m. as sentence boundaries.
        """
        sentences = re.split(
            r"(?<=[!?;])\s+|(?<!\b(?:a|p))\.(?=\s+[A-Z])",
            text,
        )

        for sentence in sentences:
            normalized = self._normalize(sentence)

            if not any(
                pattern.search(normalized)
                for pattern in patterns
            ):
                continue

            matched_topic_terms = sum(
                1
                for term in topic_terms
                if self._contains_term(normalized, term)
            )

            required_topic_terms = (
                2
                if len(topic_terms) >= 4
                else 1
            )

            if matched_topic_terms >= required_topic_terms:
                return True

        return False

    def _has_quantitative_or_limit_signal(
        self,
        text: str,
    ) -> bool:
        normalized = self._normalize(text)

        return bool(
            re.search(
                r"\b\d+(?:\.\d+)?\s*(?:%|percent)\b",
                normalized,
            )
            or re.search(
                r"(?:rs\.?|rupees?)\s*[\d,]+(?:\.\d+)?",
                normalized,
            )
            or re.search(
                r"\b\d+(?:\.\d+)?\s*(?:crore|lakh|million|billion)\b",
                normalized,
            )
            or re.search(
                r"\b(?:threshold|limit|maximum|minimum)\b",
                normalized,
            )
        )

    def _threshold_is_topic_anchored(
        self,
        text: str,
        topic_terms: list[str],
    ) -> bool:
        """Require a positive quantitative/limit signal tied to the topic."""
        sentences = re.split(
            r"(?<=[.!?;])\s+",
            text,
        )

        quantitative = re.compile(
            r"(?:\b\d+(?:\.\d+)?\s*(?:%|percent|crore|lakh|"
            r"million|billion)(?![a-z0-9])"
            r"|(?:₹|rs\.?|rupees?)\s*[\d,]+(?:\.\d+)?"
            r"|\b(?:threshold|limit|maximum|minimum)\b)",
            re.I,
        )

        negative = re.compile(
            r"\b(?:no|not|without|none|neither|unrelated|irrelevant)\b"
            r"|\b(?:does|do|did)\s+not\b"
            r"|\bnot\s+related\b",
            re.I,
        )

        for sentence in sentences:
            normalized = self._normalize(
                sentence
            )

            if not quantitative.search(
                normalized
            ):
                continue

            if negative.search(
                normalized
            ):
                continue

            if (
                not topic_terms
                or any(
                    self._contains_term(
                        normalized,
                        term,
                    )
                    for term in topic_terms
                )
            ):
                return True

        return False

    def _has_actual_penalty_signal(
        self,
        text: str,
    ) -> bool:
        normalized = self._normalize(text)

        return bool(
            re.search(
                r"\b(?:penalt(?:y|ies)|fine|fines)"
                r"\s+(?:of|up\s+to|may|shall|will|"
                r"applies?|apply)\b",
                normalized,
            )
            or re.search(
                r"\bpunishable\s+(?:with|by)\b",
                normalized,
            )
            or re.search(
                r"\b(?:imprisonment|prosecution)\b",
                normalized,
            )
            or re.search(
                r"\bcriminal\s+(?:offen[cs]e|liability|"
                r"proceedings?|action)\b",
                normalized,
            )
            or re.search(
                r"\bliable\b.{0,120}\b(?:fine|penalty|"
                r"imprisonment|prosecution|punish)",
                normalized,
            )
        )

    def _topic_coverage_is_sufficient(
        self,
        topic_terms: list[str],
        coverage: float,
    ) -> bool:
        if not topic_terms:
            return True

        if len(topic_terms) == 1:
            return coverage >= 1.0

        if len(topic_terms) <= 3:
            return coverage >= 0.67

        return coverage >= 0.40

    def _contains_term(
        self,
        text: str,
        term: str,
    ) -> bool:
        text_tokens = set(
            re.findall(
                r"[a-z0-9]+",
                text.lower(),
            )
        )

        variants = self._word_variants(
            term
        )

        return bool(
            text_tokens.intersection(
                variants
            )
        )

    def _word_variants(
        self,
        term: str,
    ) -> set[str]:
        """Match common singular/plural forms and existing verb variants."""
        normalized = term.lower()
        variants = {normalized}

        # Common singular/plural forms in both directions.
        if normalized.endswith("ies") and len(normalized) > 3:
            variants.add(normalized[:-3] + "y")
        elif normalized.endswith(("ches", "shes", "xes", "zes", "sses")):
            variants.add(normalized[:-2])
        elif normalized.endswith("s") and not normalized.endswith(
            ("ss", "us", "is")
        ):
            variants.add(normalized[:-1])
        elif (
            normalized.endswith("y")
            and len(normalized) > 1
            and normalized[-2] not in "aeiou"
        ):
            variants.add(normalized[:-1] + "ies")
        elif normalized.endswith(("s", "x", "z", "ch", "sh")):
            variants.add(normalized + "es")
        else:
            variants.add(normalized + "s")

        # Retain the existing basic verb-form matching.
        if normalized.endswith("e") and len(normalized) > 2:
            variants.add(normalized[:-1] + "ing")
        if normalized.endswith("ing") and len(normalized) > 4:
            variants.add(normalized[:-3])
        if normalized.endswith("ed") and len(normalized) > 3:
            variants.add(normalized[:-2])

        return variants

    def _best_concept_density(
        self,
        terms: list[str],
        results: list[dict],
    ) -> float:
        if not terms or not results:
            return 0.0

        best = 0.0

        for result in results:
            text = result.get(
                "text",
                "",
            )

            matched = sum(
                self._contains_term(
                    text,
                    term,
                )
                for term in terms
            )

            best = max(
                best,
                matched / len(terms),
            )

        return best

    def _is_substantive(
        self,
        result: dict,
        intents: list[str] | None = None,
    ) -> bool:
        """Determine whether retrieved text is substantive enough to evaluate.

        Normal policy chunks should contain at least 100 characters.

        A shorter chunk is also accepted when it is a complete, traceable
        policy clause containing a strong answer-bearing signal. This prevents
        short but valid requirements such as:

            "Applicants must submit a vehicle registration certificate."

        from being incorrectly discarded.
        """
        text = result.get("text")

        if not isinstance(text, str):
            return False

        normalized = text.strip()

        if not normalized:
            return False

        # Normal full-size policy chunk.
        if len(normalized) >= 100:
            return True

        intents = intents or []

        # ---------------------------------------------------------------
        # Short document requirement.
        # ---------------------------------------------------------------
        if "document_requirement" in intents:
            return self._short_document_requirement_is_substantive(
                normalized
            )

        # ---------------------------------------------------------------
        # Short generic policy rule.
        # ---------------------------------------------------------------
        if "rule" in intents:
            return bool(
                re.search(
                    r"\b(?:must|shall|should|may|prohibited|"
                    r"permitted|required|mandatory)\b",
                    normalized,
                    re.I,
                )
            )

        # ---------------------------------------------------------------
        # Short procedural clause.
        # ---------------------------------------------------------------
        if "procedure" in intents:
            return bool(
                re.search(
                    r"\b(?:must|shall|should)\s+"
                    r"(?:submit|provide|file|report|record|"
                    r"notify|sanction|obtain|verify|identify)\b",
                    normalized,
                    re.I,
                )
            )

        # ---------------------------------------------------------------
        # Short timing clause.
        # ---------------------------------------------------------------
        if "timing" in intents:
            return bool(
                re.search(
                    r"\b(?:effective|within|before|after|"
                    r"prior\s+to|deadline|days?|months?|years?)\b",
                    normalized,
                    re.I,
                )
            )

        # ---------------------------------------------------------------
        # Short threshold clause.
        # ---------------------------------------------------------------
        if "threshold" in intents:
            return self._has_quantitative_or_limit_signal(
                normalized
            )

        # ---------------------------------------------------------------
        # Short penalty clause.
        # ---------------------------------------------------------------
        if "penalty" in intents:
            return self._has_actual_penalty_signal(
                normalized
            )

        # ---------------------------------------------------------------
        # Short definition clause.
        # ---------------------------------------------------------------
        if "definition" in intents:
            return bool(
                re.search(
                    r"\b(?:means?|refers?\s+to|defined\s+as|"
                    r"shall\s+mean|is\s+(?:a|an|the))\b",
                    normalized,
                    re.I,
                )
            )

        # For all other intents, preserve the conservative 100-character
        # requirement.
        return False

    def _short_document_requirement_is_substantive(
        self,
        text: str,
    ) -> bool:
        """Accept a short but complete document-requirement policy clause."""

        normalized = self._normalize(text)

        document_signal = re.search(
            r"\b(?:document|documents|paperwork|documentation|"
            r"certificate|certificates|record|records|statement|"
            r"statements|proof|license|licence|registration|"
            r"insurance|policy|deed|agreement|identity|"
            r"identification|form|forms|application|applications)\b",
            normalized,
            re.I,
        )

        submission_signal = re.search(
            r"\b(?:must|shall|should|required|mandatory|necessary)\b"
            r".{0,100}"
            r"\b(?:submit|submitted|provide|provided|produce|"
            r"produced|furnish|furnished|present|presented|"
            r"attach|attached|upload|uploaded|include|included|"
            r"contain|contains)\b",
            normalized,
            re.I | re.S,
        )

        reverse_submission_signal = re.search(
            r"\b(?:submit|submitted|provide|provided|produce|"
            r"produced|furnish|furnished|present|presented|"
            r"attach|attached|upload|uploaded|include|included|"
            r"contain|contains)\b"
            r".{0,100}"
            r"\b(?:must|shall|should|required|mandatory|necessary)\b",
            normalized,
            re.I | re.S,
        )

        required_document_signal = re.search(
            r"\b(?:required|mandatory|necessary)\s+"
            r"(?:document|documents|paperwork|documentation|"
            r"certificate|certificates|record|records|"
            r"statement|statements|proof|license|licence|"
            r"registration|insurance|form|forms|application|applications)\b",
            normalized,
            re.I,
        )

        return bool(
            document_signal
            and (
                submission_signal
                or reverse_submission_signal
                or required_document_signal
            )
        )

    def _has_provenance(
        self,
        result: dict,
    ) -> bool:
        required_fields = (
            "chunk_id",
            "document_id",
            "source",
        )

        return all(
            isinstance(result.get(field), str)
            and result.get(field).strip()
            for field in required_fields
        )

    def _normalize(
        self,
        text: str,
    ) -> str:
        return " ".join(
            re.findall(
                r"[a-z0-9₹%]+",
                text.lower()
                .replace("–", "-")
                .replace("—", "-"),
            )
        )

    def _empty_result(
        self,
        reason: str,
        evaluated_results: int = 0,
    ) -> dict:
        return {
            "evidence_status": "insufficient",
            "reason": reason,
            "matched_terms": [],
            "covered_requirements": [],
            "missing_requirements": [],
            "requirement_details": [],
            "evaluated_results": evaluated_results,
            "substantive_results": 0,
            "provenance_results": 0,
            "term_coverage": 0.0,
            "concept_density": 0.0,
        }
