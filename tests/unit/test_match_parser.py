"""Unit tests for the server-side match-JSON extractor."""
from backend.app.services.match_parser import extract_matches

FENCED_ANSWER = """Here are two solid options.

```json
{
  "matches": [
    {
      "title": "AI Learning Engineer",
      "company": "Acme",
      "requirements": ["python", "pytorch"],
      "score": 92,
      "source_file": "acme.pdf",
      "document_id": "doc-1"
    },
    {
      "title": "Data Intern",
      "company": "Globex",
      "requirements": ["sql"],
      "score": 70,
      "source_file": "globex.pdf",
      "document_id": "doc-2"
    }
  ]
}
```"""


def test_extracts_fenced_json_and_strips_block():
    cleaned, matches = extract_matches(FENCED_ANSWER)
    assert "```json" not in cleaned
    assert cleaned.strip().startswith("Here are two solid options.")

    assert len(matches) == 2
    assert matches[0].title == "AI Learning Engineer"
    assert matches[0].score == 92
    assert matches[0].requirements == ["python", "pytorch"]
    assert matches[1].document_id == "doc-2"


def test_handles_unfenced_json_with_surrounding_prose():
    raw = (
        "Two relevant internships:\n"
        '{"matches": [{"title": "Backend Intern", "company": "Foo", "score": 80}]}'
    )
    cleaned, matches = extract_matches(raw)
    assert cleaned.strip() == "Two relevant internships:"
    assert len(matches) == 1
    assert matches[0].title == "Backend Intern"
    assert matches[0].company == "Foo"
    assert matches[0].score == 80


def test_clamps_score_to_0_100():
    raw = '```json\n{"matches": [{"title": "A", "score": 250}, {"title": "B", "score": -5}]}\n```'
    _, matches = extract_matches(raw)
    assert matches[0].score == 100
    assert matches[1].score == 0


def test_coerces_non_string_requirements_and_drops_empties():
    raw = '```json\n{"matches": [{"title": "A", "requirements": ["python", "", null, 3]}]}\n```'
    _, matches = extract_matches(raw)
    assert matches[0].requirements == ["python", "3"]


def test_drops_match_entries_without_title_or_company():
    raw = (
        '```json\n{"matches": ['
        '{"score": 50},'
        '{"title": "Real", "company": "Co"},'
        '{"company": "Just a company"}'
        "]}\n```"
    )
    _, matches = extract_matches(raw)
    titles = [m.title for m in matches]
    assert "Real" in titles
    assert "Just a company" in titles  # title falls back to company
    assert len(matches) == 2


def test_returns_empty_when_no_json_present():
    raw = "Just plain prose with no JSON anywhere."
    cleaned, matches = extract_matches(raw)
    assert cleaned == raw
    assert matches == []


def test_returns_empty_on_invalid_json():
    raw = "```json\n{matches: not_json}\n```"
    cleaned, matches = extract_matches(raw)
    # Parser bails — leaves the answer untouched so the user still sees something.
    assert cleaned == raw
    assert matches == []


def test_returns_empty_when_matches_field_missing():
    raw = '```json\n{"unrelated": [1, 2, 3]}\n```'
    cleaned, matches = extract_matches(raw)
    assert matches == []


def test_empty_answer():
    cleaned, matches = extract_matches("")
    assert cleaned == ""
    assert matches == []
