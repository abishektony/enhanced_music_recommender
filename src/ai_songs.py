"""Use Gemini to generate new song entries and append them to data/songs.csv."""

import csv, json, os, time
from pathlib import Path
from urllib import error as urllib_error, request as urllib_request

CSV_PATH = Path("data/songs.csv")
CSV_FIELDS = [
    "id","title","artist","genre","mood","energy","tempo_bpm","valence",
    "danceability","acousticness","popularity","release_year","release_decade",
    "instrumentalness","liveness","speechiness","detailed_mood_tags",
]

def _next_id(rows):
    return max((int(r.get("id",0)) for r in rows), default=0) + 1

def _existing_titles(rows):
    return {(r.get("title","").lower(), r.get("artist","").lower()) for r in rows}

def _load():
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _save(rows):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def fetch_via_gemini(genre: str, mood: str, count: int, api_key: str, model: str) -> list[dict]:
    """Ask Gemini to generate `count` realistic songs and return new rows added."""
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={api_key}"
    )
    prompt = (
        f"Generate {count} realistic song entries for a music dataset. "
        f"Focus on genre='{genre}' and mood='{mood}'. "
        "Return a JSON array where each object has exactly these keys: "
        "title, artist, genre, mood, energy (0-1 float), tempo_bpm (float), "
        "valence (0-1), danceability (0-1), acousticness (0-1), popularity (0-100 int), "
        "release_year (int 1970-2025), instrumentalness (0-1), liveness (0-1), "
        "speechiness (0-1), detailed_mood_tags (pipe-separated string like 'happy|dance'). "
        "Use real or plausible artist names and song titles. "
        "Return ONLY the JSON array, no extra text."
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    for attempt in range(3):
        try:
            req = urllib_request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib_request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode())
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            songs = json.loads(text)
            if not isinstance(songs, list):
                return []

            existing = _load()
            known    = _existing_titles(existing)
            next_id  = _next_id(existing)
            new_rows = []

            for s in songs:
                key = (str(s.get("title","")).lower(), str(s.get("artist","")).lower())
                if key in known:
                    continue
                ry = int(s.get("release_year", 2020))
                row = {
                    "id": next_id,
                    "title": s.get("title","Unknown"),
                    "artist": s.get("artist","Unknown"),
                    "genre": s.get("genre", genre),
                    "mood": s.get("mood", mood),
                    "energy": round(float(s.get("energy", 0.5)), 4),
                    "tempo_bpm": round(float(s.get("tempo_bpm", 120)), 1),
                    "valence": round(float(s.get("valence", 0.5)), 4),
                    "danceability": round(float(s.get("danceability", 0.5)), 4),
                    "acousticness": round(float(s.get("acousticness", 0.3)), 4),
                    "popularity": float(s.get("popularity", 60)),
                    "release_year": ry,
                    "release_decade": (ry // 10) * 10,
                    "instrumentalness": round(float(s.get("instrumentalness", 0.1)), 4),
                    "liveness": round(float(s.get("liveness", 0.4)), 4),
                    "speechiness": round(float(s.get("speechiness", 0.1)), 4),
                    "detailed_mood_tags": s.get("detailed_mood_tags", mood),
                }
                new_rows.append(row)
                known.add(key)
                next_id += 1

            if new_rows:
                _save(existing + new_rows)
            return new_rows

        except urllib_error.HTTPError as e:
            if e.code in {429, 503} and attempt < 2:
                time.sleep(5 * (attempt + 1)); continue
            raise
        except Exception:
            raise
    return []
