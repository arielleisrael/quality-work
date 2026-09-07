from tools.capture import naming


def test_slugify_takes_first_words_lowercased():
    assert naming.slugify("The checklist keeps growing") == "the-checklist-keeps-growing"


def test_slugify_truncates_to_max_words():
    text = "one two three four five six seven eight"
    assert naming.slugify(text) == "one-two-three-four-five-six"


def test_slugify_strips_punctuation():
    assert naming.slugify("Won't it, though?") == "won-t-it-though"


def test_slugify_collapses_repeated_separators():
    assert naming.slugify("a  --  b") == "a-b"


def test_slugify_falls_back_when_no_usable_characters():
    assert naming.slugify("!!! ???") == "untitled"


def test_body_hash_is_stable():
    assert naming.body_hash("hello world") == naming.body_hash("hello world")


def test_body_hash_ignores_whitespace_and_case():
    assert naming.body_hash("Hello   world\n") == naming.body_hash("hello world")


def test_body_hash_distinguishes_different_text():
    assert naming.body_hash("hello world") != naming.body_hash("goodbye world")
