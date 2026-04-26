"""
Fetch real songs from the Spotify Web API and append them to data/songs.csv.

Requirements:
  - SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in your .env file
  - Get free credentials at: https://developer.spotify.com/dashboard

Usage:
  uv run python src/fetch_songs.py                        # default genres, 20 tracks each
  uv run python src/fetch_songs.py --genres pop rock --limit 50
  uv run python src/fetch_songs.py --genres lofi --limit 30 --no-dedup
"""

import argparse
import base64
import csv
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LOGGER = logging.getLogger("fetch_songs")

# ── Spotify API constants ─────────────────────────────────────────────────────
TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"
AUDIO_FEATURES_URL = "https://api.spotify.com/v1/audio-features"

# Maps genre keywords → Spotify search queries
GENRE_QUERIES: Dict[str, str] = {
    "pop":        "genre:pop",
    "lofi":       "lo-fi chill",
    "rock":       "genre:rock",
    "rap":        "genre:hip-hop",
    "jazz":       "genre:jazz",
    "electronic": "genre:electronic",
    "indie":      "genre:indie",
    "rnb":        "genre:r-n-b",
    "classical":  "genre:classical",
    "metal":      "genre:metal",
    "country":    "genre:country",
    "latin":      "genre:latin",
}

# Spotify's "valence" already maps well to mood, so we derive mood from it
def _valence_to_mood(valence: float, energy: float) -> str:
    if valence >= 0.75 and energy >= 0.7:
        return "happy"
    if valence >= 0.6:
        return "euphoric" if energy >= 0.7 else "relaxed"
    if valence >= 0.45:
        return "chill" if energy < 0.5 else "focused"
    if energy >= 0.75:
        return "intense"
    return "melancholic"


def _valence_to_tags(valence: float, energy: float, acousticness: float) -> str:
    tags = []
    if energy >= 0.75:
        tags.append("high_energy")
    else:
        tags.append("low_energy")
    if valence >= 0.6:
        tags.append("happy")
        tags.append("uplifting")
    elif valence < 0.4:
        tags.append("dark")
        tags.append("moody")
    if acousticness >= 0.6:
        tags.append("acoustic")
    if energy >= 0.65 and valence >= 0.5:
        tags.append("dance")
    return "|".join(tags) if tags else "general"


# ── Spotify auth ──────────────────────────────────────────────────────────────
class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0

    def _refresh_token(self) -> None:
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        data = urllib_parse.urlencode({"grant_type": "client_credentials"}).encode()
        req = urllib_request.Request(
            TOKEN_URL,
            data=data,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib_request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
        self._token = body["access_token"]
        self._token_expiry = time.time() + body.get("expires_in", 3600) - 60

    @property
    def token(self) -> str:
        if not self._token or time.time() >= self._token_expiry:
            self._refresh_token()
        return self._token  # type: ignore[return-value]

    def _get(self, url: str, params: Dict) -> Dict:
        full_url = url + "?" + urllib_parse.urlencode(params)
        req = urllib_request.Request(
            full_url,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        for attempt in range(3):
            try:
                with urllib_request.urlopen(req, timeout=20) as resp:
                    return json.loads(resp.read().decode())
            except urllib_error.HTTPError as exc:
                if exc.code == 429:
                    retry_after = int(exc.headers.get("Retry-After", 5))
                    LOGGER.warning("Rate limited. Waiting %ds…", retry_after)
                    time.sleep(retry_after)
                elif exc.code in {500, 502, 503}:
                    LOGGER.warning("Server error %d, retrying…", exc.code)
                    time.sleep(3 * (attempt + 1))
                else:
                    raise
        return {}

    def search_tracks(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Search for tracks; returns up to `limit` track objects."""
        result = self._get(SEARCH_URL, {
            "q": query,
            "type": "track",
            "limit": min(limit, 50),
            "offset": offset,
        })
        return result.get("tracks", {}).get("items", [])

    def audio_features(self, track_ids: List[str]) -> List[Optional[Dict]]:
        """Fetch audio features for up to 100 track IDs at once."""
        if not track_ids:
            return []
        result = self._get(AUDIO_FEATURES_URL, {"ids": ",".join(track_ids)})
        return result.get("audio_features", [])


# ── CSV helpers ───────────────────────────────────────────────────────────────
CSV_PATH = Path("data/songs.csv")
CSV_FIELDS = [
    "id", "title", "artist", "genre", "mood", "energy", "tempo_bpm",
    "valence", "danceability", "acousticness", "popularity",
    "release_year", "release_decade", "instrumentalness",
    "liveness", "speechiness", "detailed_mood_tags",
]


def _load_existing(csv_path: Path) -> tuple[List[Dict], int, set]:
    """Return (rows, max_id, existing_spotify_ids)."""
    if not csv_path.exists():
        return [], 0, set()
    rows = []
    max_id = 0
    existing_ids: set = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
            max_id = max(max_id, int(row.get("id", 0)))
            if row.get("spotify_id"):
                existing_ids.add(row["spotify_id"])
    return rows, max_id, existing_ids


def _save(csv_path: Path, rows: List[Dict]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── Main fetch logic ──────────────────────────────────────────────────────────
def fetch_and_append(
    client: SpotifyClient,
    genre: str,
    limit: int,
    dedup: bool,
) -> int:
    """Fetch `limit` tracks for `genre`, append new ones to CSV. Returns count added."""
    query = GENRE_QUERIES.get(genre.lower(), f"genre:{genre}")
    LOGGER.info("Searching Spotify for '%s' (query: %s, limit: %d)…", genre, query, limit)

    existing_rows, next_id, existing_spotify_ids = _load_existing(CSV_PATH)

    tracks_needed = limit
    offset = 0
    new_rows: List[Dict] = []
    seen_this_run: set = set()

    while tracks_needed > 0:
        batch = client.search_tracks(query, limit=min(tracks_needed, 50), offset=offset)
        if not batch:
            break

        # Filter dupes
        fresh = [
            t for t in batch
            if t["id"] not in existing_spotify_ids and t["id"] not in seen_this_run
        ] if dedup else batch

        # Fetch audio features in one call
        ids = [t["id"] for t in fresh]
        features_list = client.audio_features(ids) if ids else []
        feat_map = {
            f["id"]: f for f in features_list if f
        }

        for track in fresh:
            feat = feat_map.get(track["id"])
            if not feat:
                continue  # skip tracks without audio analysis

            release_date = track.get("album", {}).get("release_date", "2020")
            try:
                release_year = int(release_date[:4])
            except (ValueError, TypeError):
                release_year = 2020
            release_decade = (release_year // 10) * 10

            energy = round(feat.get("energy", 0.5), 4)
            valence = round(feat.get("valence", 0.5), 4)
            acousticness = round(feat.get("acousticness", 0.3), 4)
            popularity = float(track.get("popularity", 50))

            mood = _valence_to_mood(valence, energy)
            tags = _valence_to_tags(valence, energy, acousticness)

            next_id += 1
            row: Dict = {
                "id": next_id,
                "title": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "genre": genre,
                "mood": mood,
                "energy": energy,
                "tempo_bpm": round(feat.get("tempo", 120.0), 1),
                "valence": valence,
                "danceability": round(feat.get("danceability", 0.5), 4),
                "acousticness": acousticness,
                "popularity": popularity,
                "release_year": release_year,
                "release_decade": release_decade,
                "instrumentalness": round(feat.get("instrumentalness", 0.1), 4),
                "liveness": round(feat.get("liveness", 0.5), 4),
                "speechiness": round(feat.get("speechiness", 0.1), 4),
                "detailed_mood_tags": tags,
            }
            new_rows.append(row)
            seen_this_run.add(track["id"])
            tracks_needed -= 1
            if tracks_needed <= 0:
                break

        offset += 50
        if offset >= 1000:  # Spotify hard cap
            break

    if new_rows:
        _save(CSV_PATH, existing_rows + new_rows)
        LOGGER.info("✓ Added %d new tracks for genre '%s'.", len(new_rows), genre)
    else:
        LOGGER.info("No new tracks found for genre '%s'.", genre)

    return len(new_rows)


# ── CLI ───────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch songs from Spotify and append to data/songs.csv"
    )
    parser.add_argument(
        "--genres",
        nargs="+",
        default=["pop", "lofi", "rock", "rap", "electronic", "indie"],
        help=f"Genres to fetch. Available presets: {', '.join(sorted(GENRE_QUERIES))}",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of tracks to fetch per genre (default: 20)",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Allow adding tracks already in the CSV",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = build_parser().parse_args()

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        LOGGER.error(
            "Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in your .env file.\n"
            "  1. Go to https://developer.spotify.com/dashboard\n"
            "  2. Create a free app → copy Client ID and Client Secret\n"
            "  3. Add them to your .env:\n"
            "       SPOTIFY_CLIENT_ID=\"your-id\"\n"
            "       SPOTIFY_CLIENT_SECRET=\"your-secret\"\n"
        )
        raise SystemExit(1)

    client = SpotifyClient(client_id, client_secret)
    total = 0
    for genre in args.genres:
        total += fetch_and_append(client, genre, args.limit, dedup=not args.no_dedup)

    LOGGER.info("Done. Total new songs added: %d", total)
    LOGGER.info("Run the recommender: uv run python src/main.py --mode auto --use-gemini --gemini-model gemini-3-flash-preview")


if __name__ == "__main__":
    main()
