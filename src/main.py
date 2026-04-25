"""CLI runner for an agentic music recommender workflow."""

import argparse
from dataclasses import dataclass
import json
import logging
import os
import textwrap
import time
from typing import Dict, List
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import quote_plus
import webbrowser

try:
    from .recommender import load_songs, recommend_songs
except ImportError:
    from recommender import load_songs, recommend_songs


USER_PROFILES = {
    "alex_pop_happy": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.8,
        "likes_acoustic": False,
        "target_valence": 0.75,
        "target_danceability": 0.80,
        "target_tempo_bpm": 120,
        "tempo_tolerance": 15,
        "target_popularity": 85,
        "target_release_decade": 2020,
        "target_instrumentalness": 0.20,
        "target_liveness": 0.62,
        "target_speechiness": 0.12,
        "preferred_tags": ["happy", "dance", "uplifting"],
    },
    "maya_lofi_chill": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.35,
        "likes_acoustic": True,
        "target_valence": 0.60,
        "target_danceability": 0.50,
        "target_tempo_bpm": 78,
        "tempo_tolerance": 18,
        "target_popularity": 65,
        "target_release_decade": 2010,
        "target_instrumentalness": 0.70,
        "target_liveness": 0.38,
        "target_speechiness": 0.10,
        "preferred_tags": ["chill", "low_energy", "acoustic"],
    },
    "ryan_rap_intense": {
        "favorite_genre": "rap",
        "favorite_mood": "intense",
        "target_energy": 0.9,
        "likes_acoustic": False,
        "target_valence": 0.45,
        "target_danceability": 0.74,
        "target_tempo_bpm": 155,
        "tempo_tolerance": 20,
        "target_popularity": 86,
        "target_release_decade": 2020,
        "target_instrumentalness": 0.15,
        "target_liveness": 0.74,
        "target_speechiness": 0.50,
        "preferred_tags": ["intense", "high_energy", "lyrical"],
    },
}

PLATFORM_LABELS: Dict[str, str] = {
    "spotify": "Spotify",
    "youtube_music": "YouTube Music",
    "apple_music": "Apple Music",
    "deezer": "Deezer",
    "soundcloud": "SoundCloud",
}

PLATFORM_SEARCH_URLS: Dict[str, str] = {
    "spotify": "https://open.spotify.com/search/{query}",
    "youtube_music": "https://music.youtube.com/search?q={query}",
    "apple_music": "https://music.apple.com/us/search?term={query}",
    "deezer": "https://www.deezer.com/search/{query}",
    "soundcloud": "https://soundcloud.com/search?q={query}",
}

ALLOWED_RANKING_MODES = {"balanced", "genre_first", "mood_first", "energy_similarity"}

LOGGER = logging.getLogger("agentic_recommender")


@dataclass
class WorkflowContext:
    """Shared context passed between workflow agents."""

    profile_name: str
    ranking_mode: str
    top_k: int
    artist_penalty: float
    platforms: List[str]
    user_prefs: Dict


@dataclass
class WorkflowReport:
    """Structured run diagnostics for plan-act-check transparency."""

    used_gemini: bool
    planner: Dict
    checker: Dict
    retries: int


class GeminiClient:
    """Minimal Gemini REST client that requests JSON-only responses."""

    def __init__(self, api_key: str | None, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_json(self, prompt: str, fallback: Dict, max_retries: int = 4) -> Dict:
        """Return JSON content from Gemini or a deterministic fallback."""
        if not self.enabled:
            return fallback

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }

        for attempt in range(max_retries):
            try:
                req = urllib_request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib_request.urlopen(req, timeout=20) as response:
                    body = json.loads(response.read().decode("utf-8"))
                text = body["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
                LOGGER.warning("Gemini returned non-dict JSON, using fallback.")
                return fallback
            except urllib_error.HTTPError as exc:
                if exc.code == 429 and attempt < max_retries - 1:
                    sleep_time = 5 * (2 ** attempt)
                    LOGGER.warning("Gemini rate limited (429). Retrying in %d seconds...", sleep_time)
                    time.sleep(sleep_time)
                    continue
                LOGGER.warning("Gemini call failed (%s). Falling back to local logic.", exc)
                return fallback
            except (ValueError, KeyError, IndexError, urllib_error.URLError, TimeoutError) as exc:
                LOGGER.warning("Gemini call failed (%s). Falling back to local logic.", exc)
                return fallback
        return fallback


class ProfileAgent:
    """Agent responsible for selecting and validating user preferences."""

    def run(self, profile_name: str) -> Dict:
        if profile_name not in USER_PROFILES:
            valid = ", ".join(sorted(USER_PROFILES.keys()))
            raise ValueError(f"Unknown profile '{profile_name}'. Available: {valid}")
        return USER_PROFILES[profile_name]


class RankingAgent:
    """Agent responsible for scoring and ranking songs."""

    def run(self, context: WorkflowContext, songs: List[Dict]) -> List[Dict]:
        ranked = recommend_songs(
            context.user_prefs,
            songs,
            k=context.top_k,
            mode=context.ranking_mode,
            artist_penalty=context.artist_penalty,
        )
        return [
            {
                "song": song,
                "score": score,
                "explanation": explanation,
            }
            for song, score, explanation in ranked
        ]


class LinkRoutingAgent:
    """Agent responsible for building platform links for each recommendation."""

    def run(self, ranked_results: List[Dict], platforms: List[str]) -> List[Dict]:
        enriched: List[Dict] = []
        for item in ranked_results:
            song = item["song"]
            query = quote_plus(f"{song.get('title', '')} {song.get('artist', '')}".strip())
            links = {
                platform: PLATFORM_SEARCH_URLS[platform].format(query=query)
                for platform in platforms
                if platform in PLATFORM_SEARCH_URLS
            }
            enriched.append({**item, "links": links})
        return enriched


class PlannerAgent:
    """Agent that plans ranking strategy before action."""

    def __init__(self, gemini: GeminiClient) -> None:
        self.gemini = gemini

    def _fallback(self, requested_mode: str, user_prefs: Dict, top_k: int, artist_penalty: float) -> Dict:
        if requested_mode != "auto":
            mode = requested_mode
        else:
            mood = str(user_prefs.get("favorite_mood", "")).lower()
            mode = "mood_first" if mood in {"chill", "happy", "intense"} else "balanced"
        return {
            "selected_mode": mode,
            "selected_top_k": max(1, min(10, int(top_k))),
            "selected_artist_penalty": max(0.0, min(0.3, float(artist_penalty))),
            "reason": "local planner fallback",
        }

    def run(self, requested_mode: str, user_prefs: Dict, top_k: int, artist_penalty: float) -> Dict:
        fallback = self._fallback(requested_mode, user_prefs, top_k, artist_penalty)
        if requested_mode != "auto" and not self.gemini.enabled:
            return fallback

        prompt = (
            "You are a planning agent for a music recommender. "
            "Return JSON with keys selected_mode, selected_top_k, selected_artist_penalty, reason. "
            f"Allowed selected_mode values: {sorted(ALLOWED_RANKING_MODES)}. "
            f"Requested mode: {requested_mode}. "
            f"User preferences: {json.dumps(user_prefs)}. "
            f"Current top_k: {top_k}. Current artist_penalty: {artist_penalty}. "
            "Keep top_k in [1,10] and artist_penalty in [0.0,0.3]."
        )
        plan = self.gemini.generate_json(prompt, fallback)

        mode = str(plan.get("selected_mode", fallback["selected_mode"]))
        if mode not in ALLOWED_RANKING_MODES:
            mode = fallback["selected_mode"]
        plan["selected_mode"] = mode
        plan["selected_top_k"] = max(1, min(10, int(plan.get("selected_top_k", fallback["selected_top_k"]))))
        plan["selected_artist_penalty"] = max(
            0.0,
            min(0.3, float(plan.get("selected_artist_penalty", fallback["selected_artist_penalty"]))),
        )
        return plan


class QualityCheckAgent:
    """Agent that evaluates recommendation quality and proposes one retry."""

    def __init__(self, gemini: GeminiClient) -> None:
        self.gemini = gemini

    def _fallback(self, ranked_results: List[Dict]) -> Dict:
        if not ranked_results:
            return {
                "quality_pass": False,
                "confidence": 0.0,
                "reason": "empty recommendation list",
                "retry_mode": "balanced",
                "retry_artist_penalty": 0.08,
            }

        artists = {
            str(item["song"].get("artist", "")).strip().lower()
            for item in ranked_results
            if item.get("song")
        }
        diversity_ratio = len(artists) / max(1, len(ranked_results))
        avg_score = sum(float(item.get("score", 0.0)) for item in ranked_results) / len(ranked_results)

        quality_pass = diversity_ratio >= 0.6 and avg_score >= 0.45
        retry_mode = "energy_similarity" if diversity_ratio < 0.6 else "mood_first"
        retry_artist_penalty = 0.1 if diversity_ratio < 0.6 else 0.06
        confidence = max(0.0, min(1.0, (diversity_ratio + min(1.0, avg_score)) / 2))

        return {
            "quality_pass": quality_pass,
            "confidence": round(confidence, 3),
            "reason": f"diversity_ratio={diversity_ratio:.3f}, avg_score={avg_score:.3f}",
            "retry_mode": retry_mode,
            "retry_artist_penalty": retry_artist_penalty,
        }

    def run(self, ranked_results: List[Dict], current_mode: str, artist_penalty: float) -> Dict:
        fallback = self._fallback(ranked_results)
        if not self.gemini.enabled:
            return fallback

        compact_rows = [
            {
                "title": item["song"].get("title"),
                "artist": item["song"].get("artist"),
                "score": item.get("score"),
            }
            for item in ranked_results
        ]
        prompt = (
            "You are a quality-check agent for recommendations. "
            "Return JSON with keys: quality_pass (bool), confidence (0..1), reason, retry_mode, retry_artist_penalty. "
            f"Allowed retry_mode values: {sorted(ALLOWED_RANKING_MODES)}. "
            f"Current mode: {current_mode}; current artist_penalty: {artist_penalty}. "
            f"Rows: {json.dumps(compact_rows)}. "
            "Only request retry if quality is low. Keep retry_artist_penalty in [0.0,0.3]."
        )

        check = self.gemini.generate_json(prompt, fallback)
        check["quality_pass"] = bool(check.get("quality_pass", fallback["quality_pass"]))
        check["confidence"] = max(0.0, min(1.0, float(check.get("confidence", fallback["confidence"]))))
        retry_mode = str(check.get("retry_mode", fallback["retry_mode"]))
        if retry_mode not in ALLOWED_RANKING_MODES:
            retry_mode = fallback["retry_mode"]
        check["retry_mode"] = retry_mode
        check["retry_artist_penalty"] = max(
            0.0,
            min(0.3, float(check.get("retry_artist_penalty", fallback["retry_artist_penalty"]))),
        )
        return check


class AgenticRecommendationWorkflow:
    """Orchestrates profile, ranking, and link-routing agents."""

    def __init__(self, use_gemini: bool = False, gemini_model: str = "gemini-2.0-flash") -> None:
        api_key = os.getenv("GEMINI_API_KEY") if use_gemini else None
        self.gemini = GeminiClient(api_key=api_key, model=gemini_model)
        self.profile_agent = ProfileAgent()
        self.planner_agent = PlannerAgent(self.gemini)
        self.ranking_agent = RankingAgent()
        self.quality_agent = QualityCheckAgent(self.gemini)
        self.link_agent = LinkRoutingAgent()
        self.last_report = WorkflowReport(
            used_gemini=self.gemini.enabled,
            planner={},
            checker={},
            retries=0,
        )

    def run(
        self,
        songs: List[Dict],
        profile_name: str,
        ranking_mode: str,
        top_k: int,
        artist_penalty: float,
        platforms: List[str],
        max_retries: int = 1,
    ) -> List[Dict]:
        user_prefs = self.profile_agent.run(profile_name)
        plan = self.planner_agent.run(ranking_mode, user_prefs, top_k, artist_penalty)

        context = WorkflowContext(
            profile_name=profile_name,
            ranking_mode=plan["selected_mode"],
            top_k=plan["selected_top_k"],
            artist_penalty=plan["selected_artist_penalty"],
            platforms=platforms,
            user_prefs=user_prefs,
        )

        ranked = self.ranking_agent.run(context, songs)
        checker = self.quality_agent.run(ranked, context.ranking_mode, context.artist_penalty)

        retries = 0
        if (not checker.get("quality_pass", True)) and max_retries > 0:
            retries = 1
            context.ranking_mode = checker["retry_mode"]
            context.artist_penalty = checker["retry_artist_penalty"]
            ranked = self.ranking_agent.run(context, songs)
            checker = self.quality_agent.run(ranked, context.ranking_mode, context.artist_penalty)

        self.last_report = WorkflowReport(
            used_gemini=self.gemini.enabled,
            planner=plan,
            checker=checker,
            retries=retries,
        )
        return self.link_agent.run(ranked, platforms)


def parse_platforms(raw_platforms: str) -> List[str]:
    """Parse and validate comma-separated platform identifiers."""
    platforms = [part.strip().lower() for part in raw_platforms.split(",") if part.strip()]
    invalid = [p for p in platforms if p not in PLATFORM_SEARCH_URLS]
    if invalid:
        valid = ", ".join(sorted(PLATFORM_SEARCH_URLS.keys()))
        raise ValueError(f"Unsupported platforms: {', '.join(invalid)}. Use: {valid}")
    return platforms or ["spotify", "youtube_music", "apple_music"]


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser for the recommender workflow."""
    parser = argparse.ArgumentParser(description="Agentic music recommender")
    parser.add_argument("--profile", default="alex_pop_happy", help="Profile key from USER_PROFILES")
    parser.add_argument("--mode", default="balanced", help="Ranking mode or auto")
    parser.add_argument("--top-k", type=int, default=5, help="Number of recommendations")
    parser.add_argument("--artist-penalty", type=float, default=0.06, help="Penalty for repeated artists")
    parser.add_argument(
        "--platforms",
        default="spotify,youtube_music,apple_music",
        help="Comma-separated platforms",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Prompt for a recommendation/platform and open in browser",
    )
    parser.add_argument(
        "--use-gemini",
        action="store_true",
        help="Use Gemini for planner/checker agents (requires GEMINI_API_KEY)",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-2.0-flash",
        help="Gemini model name",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Maximum plan-check retry attempts",
    )
    parser.add_argument(
        "--show-agent-log",
        action="store_true",
        help="Print planner/checker diagnostics",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    """Guardrails for user-provided CLI arguments."""
    if args.mode != "auto" and args.mode not in ALLOWED_RANKING_MODES:
        valid = ", ".join(sorted(ALLOWED_RANKING_MODES | {"auto"}))
        raise ValueError(f"Unsupported mode '{args.mode}'. Use: {valid}")
    if args.top_k < 1 or args.top_k > 10:
        raise ValueError("--top-k must be between 1 and 10")
    if args.artist_penalty < 0 or args.artist_penalty > 0.3:
        raise ValueError("--artist-penalty must be between 0.0 and 0.3")
    if args.max_retries < 0 or args.max_retries > 3:
        raise ValueError("--max-retries must be between 0 and 3")


def _print_table(recommendations: List[Dict], profile_name: str, ranking_mode: str) -> None:
    """Print recommendations in a transparent ASCII table."""
    title_w = 22
    artist_w = 24
    score_w = 7
    reasons_w = 68

    print("\n" + "=" * 146)
    print(f"TOP RECOMMENDATIONS | profile={profile_name} | mode={ranking_mode}")
    print("=" * 146)
    header = f"| {'#':^3} | {'Title':<{title_w}} | {'Artist':<{artist_w}} | {'Score':>{score_w}} | {'Reasons':<{reasons_w}} |"
    sep = f"+-{'-'*3}-+-{'-'*title_w}-+-{'-'*artist_w}-+-{'-'*score_w}-+-{'-'*reasons_w}-+"
    print(sep)
    print(header)
    print(sep)

    for rank, item in enumerate(recommendations, start=1):
        song = item["song"]
        score = item["score"]
        explanation = item["explanation"]
        wrapped_reasons = textwrap.wrap(explanation, width=reasons_w) or [""]
        for idx, reason_line in enumerate(wrapped_reasons):
            rank_cell = f"{rank:^3}" if idx == 0 else " " * 3
            title_cell = song["title"][:title_w] if idx == 0 else ""
            artist_cell = song["artist"][:artist_w] if idx == 0 else ""
            score_cell = f"{score:.3f}" if idx == 0 else ""
            print(
                f"| {rank_cell} | {title_cell:<{title_w}} | {artist_cell:<{artist_w}} | {score_cell:>{score_w}} | {reason_line:<{reasons_w}} |"
            )
        print(sep)


def _print_links(recommendations: List[Dict]) -> None:
    """Print available open links grouped by recommendation."""
    print("\nOPEN LINKS")
    print("=" * 146)
    for idx, item in enumerate(recommendations, start=1):
        song = item["song"]
        print(f"{idx}. {song['title']} - {song['artist']}")
        for platform, url in item.get("links", {}).items():
            label = PLATFORM_LABELS.get(platform, platform)
            print(f"   [{label}] {url}")


def _prompt_open_link(recommendations: List[Dict]) -> None:
    """Prompt user for a recommendation and platform to open in browser."""
    if not recommendations:
        return

    selected = input("\nOpen a song link in browser? (y/n): ").strip().lower()
    if selected not in {"y", "yes"}:
        return

    rank_value = input(f"Select song number (1-{len(recommendations)}): ").strip()
    if not rank_value.isdigit():
        print("Invalid song selection. Skipping browser open.")
        return

    rank = int(rank_value)
    if rank < 1 or rank > len(recommendations):
        print("Song selection out of range. Skipping browser open.")
        return

    item = recommendations[rank - 1]
    links = item.get("links", {})
    if not links:
        print("No platforms available for this recommendation.")
        return

    options = ", ".join(sorted(links.keys()))
    platform = input(f"Choose platform ({options}): ").strip().lower()
    if platform not in links:
        print("Unsupported platform selection. Skipping browser open.")
        return

    webbrowser.open_new_tab(links[platform])
    print(f"Opened {PLATFORM_LABELS.get(platform, platform)} for {item['song']['title']}.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    _validate_args(args)
    songs = load_songs("data/songs.csv")
    platforms = parse_platforms(args.platforms)

    workflow = AgenticRecommendationWorkflow(use_gemini=args.use_gemini, gemini_model=args.gemini_model)
    recommendations = workflow.run(
        songs=songs,
        profile_name=args.profile,
        ranking_mode=args.mode,
        top_k=args.top_k,
        artist_penalty=args.artist_penalty,
        platforms=platforms,
        max_retries=args.max_retries,
    )

    if args.show_agent_log:
        print("\nAGENT RUN REPORT")
        print("=" * 146)
        print(f"Used Gemini: {workflow.last_report.used_gemini}")
        print(f"Planner: {workflow.last_report.planner}")
        print(f"Checker: {workflow.last_report.checker}")
        print(f"Retries: {workflow.last_report.retries}")

    _print_table(recommendations, args.profile, args.mode)
    _print_links(recommendations)

    if args.open_browser:
        _prompt_open_link(recommendations)


if __name__ == "__main__":
    main()
