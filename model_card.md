# Model Card: Enhanced Agentic Music Recommender

**Limitations and Biases:** The primary limitation is the small base dataset (30 songs). The system naturally favors popular, mainstream genres. Niche listeners receive loosely related tracks that may not reflect their intent, marginalizing underrepresented musical genres. The AI song fetcher partially mitigates this by allowing targeted genre expansion.

**Misuse Prevention:** The `RankingAgent` algorithm is fully deterministic — the LLM cannot arbitrarily suppress artists. The `LinkRoutingAgent` constructs URLs via structured search queries rather than allowing the AI to generate arbitrary links.

**Testing Surprises:** The AI evaluator's ability to detect its own filter bubbles was unexpected. When forced into `artist_penalty=0.0`, the `QualityCheckAgent` correctly identified the diversity problem and failed the quality check without prompting.

**AI Collaboration:**
  - *Helpful:* Gemini was highly effective at generating the Mermaid.js architecture diagram and producing structured JSON song data with realistic audio feature distributions.
  - *Flawed:* Initial Gemini model name recommendations (`gemini-2.0-flash-lite` without `-001`, `gemini-3.1-flash-lite` without `-preview`) caused HTTP 404 errors that required manual debugging against the live models list endpoint. But more often then not the AI was helpful and gave me correct suggestions.