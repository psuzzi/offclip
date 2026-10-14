"""Slides: turn a clip into a Markdown study deck (one folder per video: slides.md, images/, meta.json).

Pipeline, one module per stage: transcript (captions → timed words → sentences), frames (one grey pass with ffmpeg),
signals (where a new section may start), segment (fuse them into sections), text, deck. The stages are pure functions
on plain data, so they are tested offline in tests/; only frames and the pipeline itself run processes or touch files.
"""
