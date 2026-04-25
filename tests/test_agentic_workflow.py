from argparse import Namespace

import pytest

from src.main import AgenticRecommendationWorkflow, _validate_args, parse_platforms


def test_parse_platforms_returns_expected_values():
    platforms = parse_platforms("spotify,youtube_music,apple_music")

    assert platforms == ["spotify", "youtube_music", "apple_music"]


def test_workflow_adds_platform_links_to_recommendations():
    songs = [
        {
            "id": 1,
            "title": "Test Pop Track",
            "artist": "Test Artist",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "tempo_bpm": 120,
            "valence": 0.9,
            "danceability": 0.8,
            "acousticness": 0.2,
            "popularity": 90,
            "release_year": 2021,
            "release_decade": 2020,
            "instrumentalness": 0.2,
            "liveness": 0.6,
            "speechiness": 0.1,
            "detailed_mood_tags": "happy|dance",
        }
    ]
    workflow = AgenticRecommendationWorkflow()

    results = workflow.run(
        songs=songs,
        profile_name="alex_pop_happy",
        ranking_mode="balanced",
        top_k=1,
        artist_penalty=0.06,
        platforms=["spotify", "youtube_music"],
    )

    assert len(results) == 1
    links = results[0]["links"]
    assert "spotify" in links
    assert "youtube_music" in links
    assert links["spotify"].startswith("https://open.spotify.com/search/")
    assert links["youtube_music"].startswith("https://music.youtube.com/search?q=")


def test_workflow_generates_plan_check_report_without_gemini():
    songs = [
        {
            "id": 1,
            "title": "Test Pop Track",
            "artist": "Artist A",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "tempo_bpm": 120,
            "valence": 0.9,
            "danceability": 0.8,
            "acousticness": 0.2,
            "popularity": 90,
            "release_year": 2021,
            "release_decade": 2020,
            "instrumentalness": 0.2,
            "liveness": 0.6,
            "speechiness": 0.1,
            "detailed_mood_tags": "happy|dance",
        }
    ]

    workflow = AgenticRecommendationWorkflow(use_gemini=False)
    workflow.run(
        songs=songs,
        profile_name="alex_pop_happy",
        ranking_mode="auto",
        top_k=1,
        artist_penalty=0.06,
        platforms=["spotify"],
        max_retries=1,
    )

    assert workflow.last_report.used_gemini is False
    assert "selected_mode" in workflow.last_report.planner
    assert "quality_pass" in workflow.last_report.checker


def test_validate_args_rejects_invalid_top_k():
    args = Namespace(
        mode="balanced",
        top_k=0,
        artist_penalty=0.06,
        max_retries=1,
    )

    with pytest.raises(ValueError):
        _validate_args(args)
