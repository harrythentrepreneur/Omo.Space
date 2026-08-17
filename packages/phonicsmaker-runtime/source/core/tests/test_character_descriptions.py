from app.phonics_maker.image_generation.image_service import (
    parse_character_descriptions,
    flatten_character_descriptions,
)


def test_parses_main_and_secondary_characters():
    block = (
        "MAIN CHARACTER: a small talking rabbit with brown fur and a red scarf\n"
        "SECONDARY CHARACTER (Coach Sam): a tall broad-shouldered human man with a whistle"
    )
    main, secondaries = parse_character_descriptions(block)
    assert main == "a small talking rabbit with brown fur and a red scarf"
    assert secondaries == [
        ("Coach Sam", "a tall broad-shouldered human man with a whistle")
    ]


def test_unlabelled_block_is_treated_as_main_description():
    block = "a green dragon with golden eyes"
    main, secondaries = parse_character_descriptions(block)
    assert main == "a green dragon with golden eyes"
    assert secondaries == []


def test_omitted_secondary_leaves_only_main():
    main, secondaries = parse_character_descriptions("MAIN CHARACTER: a shy owl")
    assert main == "a shy owl"
    assert secondaries == []


def test_handles_empty_or_none():
    assert parse_character_descriptions(None) == (None, [])
    assert parse_character_descriptions("") == (None, [])
    assert flatten_character_descriptions(None) is None


def test_flatten_strips_labels_but_keeps_names():
    block = (
        "MAIN CHARACTER: a small talking rabbit\n"
        "SECONDARY CHARACTER (Coach Sam): a tall man with a whistle"
    )
    assert flatten_character_descriptions(block) == (
        "a small talking rabbit Coach Sam: a tall man with a whistle"
    )


def test_flatten_of_unlabelled_block_is_unchanged():
    assert flatten_character_descriptions("a green dragon") == "a green dragon"
