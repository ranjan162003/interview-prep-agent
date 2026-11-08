import pytest

from app.agents.llm_json import extract_json_object, generate_validated_json
from app.core.app_exceptions import AgentResponseParseError
from app.learning.duplicate_detector import find_duplicate, fingerprint, normalize_text
from app.schemas.agent_output_schemas import GeneratedQuiz


def test_fingerprint_ignores_case_punctuation_and_spacing() -> None:
    assert fingerprint("What is a Hash Map?") == fingerprint("what is a   hash map")


def test_reworded_question_is_a_near_duplicate() -> None:
    seen = [normalize_text("What is the time complexity of binary search on a sorted array?")]
    assert find_duplicate("What is the time complexity of a binary search on a sorted array?", seen)


def test_different_question_on_same_topic_is_not_a_duplicate() -> None:
    seen = [normalize_text("What is the time complexity of binary search on a sorted array?")]
    assert find_duplicate("Why must the array be sorted before running binary search?", seen) is None


def test_short_questions_need_character_similarity_not_just_shared_words() -> None:
    seen = [normalize_text("What is a stack?")]
    assert find_duplicate("What is a queue?", seen) is None


def test_extracts_json_from_fences_prose_and_stray_quotes() -> None:
    reply = 'Sure! ```json\n{"note": "the "best" answer", "n": 1}\n``` Hope that helps {not json}'
    assert extract_json_object(reply) == {"note": 'the "best" answer', "n": 1}


def test_cut_off_reply_is_reported_as_cut_off() -> None:
    with pytest.raises(AgentResponseParseError, match="cut off"):
        extract_json_object('{"questions": [{"question": "What is')


def test_bad_reply_gets_one_repair_retry(provider) -> None:
    good = {
        "questions": [
            {"question": "Which is O(1) average lookup?", "options": ["list", "dict", "tuple", "str"],
             "correct_index": 1, "explanation": "Hash table.", "key_point": "Dicts are hash tables."}
        ]
    }
    provider.queue("I can't do JSON today", good)
    quiz = generate_validated_json(provider, None, "prompt", GeneratedQuiz)
    assert quiz.questions[0].correct_index == 1
    assert "could not be used" in provider.prompts[1]
