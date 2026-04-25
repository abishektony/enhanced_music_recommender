from typing import List, Dict, Tuple, Literal
from dataclasses import dataclass
import csv

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    popularity: float = 50.0
    release_year: int = 2010
    release_decade: int = 2010
    instrumentalness: float = 0.5
    liveness: float = 0.5
    speechiness: float = 0.2
    detailed_mood_tags: str = ""

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_popularity: float = 65.0
    target_release_decade: int = 2010
    target_instrumentalness: float = 0.5
    target_liveness: float = 0.5
    target_speechiness: float = 0.2

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5, mode: str = "balanced") -> List[Song]:
        scored: List[Tuple[Song, float, List[str]]] = []
        user_dict = {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
            "target_popularity": user.target_popularity,
            "target_release_decade": user.target_release_decade,
            "target_instrumentalness": user.target_instrumentalness,
            "target_liveness": user.target_liveness,
            "target_speechiness": user.target_speechiness,
        }

        for song in self.songs:
            song_dict = {
                "genre": song.genre,
                "mood": song.mood,
                "energy": song.energy,
                "tempo_bpm": song.tempo_bpm,
                "valence": song.valence,
                "danceability": song.danceability,
                "acousticness": song.acousticness,
                "popularity": song.popularity,
                "release_year": song.release_year,
                "release_decade": song.release_decade,
                "instrumentalness": song.instrumentalness,
                "liveness": song.liveness,
                "speechiness": song.speechiness,
                "detailed_mood_tags": song.detailed_mood_tags,
                "artist": song.artist,
            }
            score, reasons = score_song(user_dict, song_dict, mode=mode)
            scored.append((song, score, reasons))

        ranked = _select_with_artist_diversity(scored, k=k)
        return [song for song, _, _ in ranked]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        user_dict = {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }
        song_dict = {
            "genre": song.genre,
            "mood": song.mood,
            "energy": song.energy,
            "tempo_bpm": song.tempo_bpm,
            "valence": song.valence,
            "danceability": song.danceability,
            "acousticness": song.acousticness,
        }
        score, reasons = score_song(user_dict, song_dict)
        if not reasons:
            return f"Overall match score: {score:.2f}."
        return f"Overall match score: {score:.2f}. " + "; ".join(reasons)


# Weighted recipe used by both OOP and functional recommenders.
BASE_WEIGHTS: Dict[str, float] = {
    "genre": 0.30,
    "mood": 0.20,
    "energy": 0.20,
    "tempo": 0.10,
    "valence": 0.08,
    "danceability": 0.07,
    "acousticness": 0.05,
    "popularity": 0.05,
    "release_decade": 0.03,
    "instrumentalness": 0.05,
    "liveness": 0.03,
    "speechiness": 0.03,
    "tag_overlap": 0.04,
}

RankingMode = Literal["balanced", "genre_first", "mood_first", "energy_similarity"]

MODE_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "balanced": {},
    "genre_first": {
        "genre": 1.45,
        "mood": 1.10,
        "energy": 0.75,
    },
    "mood_first": {
        "mood": 1.50,
        "genre": 1.00,
        "energy": 0.75,
    },
    "energy_similarity": {
        "energy": 1.55,
        "tempo": 1.25,
        "genre": 0.75,
        "mood": 0.80,
    },
}


def get_mode_weights(mode: str) -> Dict[str, float]:
    """Return mode-specific weights using a strategy map."""
    multipliers = MODE_MULTIPLIERS.get(mode, MODE_MULTIPLIERS["balanced"])
    return {
        key: round(value * multipliers.get(key, 1.0), 4)
        for key, value in BASE_WEIGHTS.items()
    }


def _closeness(target: float, value: float, max_delta: float) -> float:
    """Return a 0-1 similarity score based on distance from the target."""
    if max_delta <= 0:
        return 0.0
    return max(0.0, 1.0 - (abs(target - value) / max_delta))


def _tag_overlap(preferred_tags: List[str], song_tag_str: str) -> float:
    """Return a 0-1 overlap ratio between preferred tags and song tags."""
    if not preferred_tags:
        return 0.0
    song_tags = {
        part.strip().lower()
        for part in song_tag_str.split("|")
        if part.strip()
    }
    if not song_tags:
        return 0.0
    pref = {tag.strip().lower() for tag in preferred_tags if str(tag).strip()}
    if not pref:
        return 0.0
    return len(pref.intersection(song_tags)) / len(pref)


def _select_with_artist_diversity(
    scored: List[Tuple[object, float, List[str]]],
    k: int,
    artist_penalty: float = 0.06,
) -> List[Tuple[object, float, List[str]]]:
    """Greedy reranker that applies an artist repetition penalty for diversity."""
    remaining = list(scored)
    selected: List[Tuple[object, float, List[str]]] = []
    artist_counts: Dict[str, int] = {}

    while remaining and len(selected) < k:
        best_idx = 0
        best_adjusted = -1.0

        for idx, (song_obj, base_score, _) in enumerate(remaining):
            artist = str(song_obj.get("artist") if isinstance(song_obj, dict) else getattr(song_obj, "artist", "")).strip().lower()
            count = artist_counts.get(artist, 0)
            adjusted = base_score - (artist_penalty * count)
            if adjusted > best_adjusted:
                best_adjusted = adjusted
                best_idx = idx

        song_obj, base_score, reasons = remaining.pop(best_idx)
        artist = str(song_obj.get("artist") if isinstance(song_obj, dict) else getattr(song_obj, "artist", "")).strip().lower()
        count = artist_counts.get(artist, 0)
        adjusted_score = round(base_score - (artist_penalty * count), 4)
        updated_reasons = list(reasons)
        if count > 0:
            updated_reasons.append(f"artist diversity penalty (-{artist_penalty * count:.3f})")

        selected.append((song_obj, adjusted_score, updated_reasons))
        artist_counts[artist] = count + 1

    return selected

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            songs.append(
                {
                    "id": int(row["id"]),
                    "title": row["title"],
                    "artist": row["artist"],
                    "genre": row["genre"],
                    "mood": row["mood"],
                    "energy": float(row["energy"]),
                    "tempo_bpm": float(row["tempo_bpm"]),
                    "valence": float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "acousticness": float(row["acousticness"]),
                    "popularity": float(row.get("popularity", 50)),
                    "release_year": int(float(row.get("release_year", 2010))),
                    "release_decade": int(float(row.get("release_decade", 2010))),
                    "instrumentalness": float(row.get("instrumentalness", 0.5)),
                    "liveness": float(row.get("liveness", 0.5)),
                    "speechiness": float(row.get("speechiness", 0.2)),
                    "detailed_mood_tags": row.get("detailed_mood_tags", ""),
                }
            )
    return songs

def score_song(user_prefs: Dict, song: Dict, mode: RankingMode = "balanced") -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py
    """
    reasons: List[str] = []
    score = 0.0
    weights = get_mode_weights(mode)

    def add_reason(label: str, points: float) -> None:
        """Append a formatted reason line when a scoring component adds points."""
        if points > 0:
            reasons.append(f"{label} (+{points:.3f})")

    favorite_genre = str(user_prefs.get("favorite_genre", user_prefs.get("genre", ""))).strip().lower()
    favorite_mood = str(user_prefs.get("favorite_mood", user_prefs.get("mood", ""))).strip().lower()

    if favorite_genre and str(song.get("genre", "")).strip().lower() == favorite_genre:
        genre_points = weights["genre"]
        score += genre_points
        add_reason("genre match", genre_points)

    if favorite_mood and str(song.get("mood", "")).strip().lower() == favorite_mood:
        mood_points = weights["mood"]
        score += mood_points
        add_reason("mood match", mood_points)

    target_energy = float(user_prefs.get("target_energy", user_prefs.get("energy", 0.5)))
    energy_match = _closeness(target_energy, float(song.get("energy", 0.5)), 1.0)
    energy_points = weights["energy"] * energy_match
    score += energy_points
    add_reason("energy closeness", energy_points)

    target_tempo = float(user_prefs.get("target_tempo_bpm", 110.0))
    tempo_tolerance = float(user_prefs.get("tempo_tolerance", 40.0))
    tempo_match = _closeness(target_tempo, float(song.get("tempo_bpm", target_tempo)), tempo_tolerance)
    tempo_points = weights["tempo"] * tempo_match
    score += tempo_points
    add_reason("tempo fit", tempo_points)

    target_valence = float(user_prefs.get("target_valence", 0.6))
    valence_match = _closeness(target_valence, float(song.get("valence", target_valence)), 1.0)
    valence_points = weights["valence"] * valence_match
    score += valence_points
    add_reason("valence match", valence_points)

    target_dance = float(user_prefs.get("target_danceability", 0.6))
    dance_match = _closeness(target_dance, float(song.get("danceability", target_dance)), 1.0)
    dance_points = weights["danceability"] * dance_match
    score += dance_points
    add_reason("danceability match", dance_points)

    likes_acoustic = bool(user_prefs.get("likes_acoustic", False))
    target_acoustic = 0.8 if likes_acoustic else 0.2
    acoustic_match = _closeness(target_acoustic, float(song.get("acousticness", target_acoustic)), 1.0)
    acoustic_points = weights["acousticness"] * acoustic_match
    score += acoustic_points
    add_reason("acousticness fit", acoustic_points)

    target_popularity = float(user_prefs.get("target_popularity", 65.0))
    pop_match = _closeness(target_popularity, float(song.get("popularity", target_popularity)), 100.0)
    pop_points = weights["popularity"] * pop_match
    score += pop_points
    add_reason("popularity fit", pop_points)

    target_decade = int(user_prefs.get("target_release_decade", 2010))
    song_decade = int(song.get("release_decade", target_decade))
    decade_match = _closeness(float(target_decade), float(song_decade), 20.0)
    decade_points = weights["release_decade"] * decade_match
    score += decade_points
    add_reason("era fit", decade_points)

    target_instr = float(user_prefs.get("target_instrumentalness", 0.6 if likes_acoustic else 0.25))
    instr_match = _closeness(target_instr, float(song.get("instrumentalness", target_instr)), 1.0)
    instr_points = weights["instrumentalness"] * instr_match
    score += instr_points
    add_reason("instrumentalness fit", instr_points)

    target_live = float(user_prefs.get("target_liveness", 0.45))
    live_match = _closeness(target_live, float(song.get("liveness", target_live)), 1.0)
    live_points = weights["liveness"] * live_match
    score += live_points
    add_reason("liveness fit", live_points)

    target_speech = float(user_prefs.get("target_speechiness", 0.25))
    speech_match = _closeness(target_speech, float(song.get("speechiness", target_speech)), 1.0)
    speech_points = weights["speechiness"] * speech_match
    score += speech_points
    add_reason("speechiness fit", speech_points)

    preferred_tags = [
        str(tag).strip().lower()
        for tag in user_prefs.get("preferred_tags", [])
        if str(tag).strip()
    ]
    tag_match = _tag_overlap(preferred_tags, str(song.get("detailed_mood_tags", "")))
    tag_points = weights["tag_overlap"] * tag_match
    score += tag_points
    add_reason("mood-tag overlap", tag_points)

    return (round(score, 4), reasons)

def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    mode: RankingMode = "balanced",
    artist_penalty: float = 0.06,
) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    scored: List[Tuple[Dict, float, List[str]]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, mode=mode)
        scored.append((song, score, reasons))

    ranked = _select_with_artist_diversity(scored, k=k, artist_penalty=artist_penalty)
    return [
        (
            song,
            score,
            ", ".join(reasons) if reasons else "general feature similarity",
        )
        for song, score, reasons in ranked
    ]
