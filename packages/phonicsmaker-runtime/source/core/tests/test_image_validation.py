#!/usr/bin/env python3
"""
Tests for image validation in _generate_single_image_with_seed().

Verifies that:
  1. Valid images pass through on the first attempt
  2. Corrupt images trigger re-generation (not re-download) with a bumped seed
  3. All attempts exhausted raises ValueError
  4. API exceptions are propagated after max attempts

Run: cd phonicsmaker-core-v1 && python -m pytest tests/test_image_validation.py -v
"""

import sys
import os
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_image_service():
    """Create an ImageService instance with mocked dependencies."""
    from app.phonics_maker.image_generation.image_service import ImageService
    svc = ImageService()
    svc._book_seed = 42
    return svc


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── 1. Happy path: valid image on first attempt ─────────────────────────

def test_valid_image_returns_immediately():
    """When validation passes on the first attempt, return the SceneImage."""
    svc = _make_image_service()

    with patch.object(svc, '_validate_remote_image', new_callable=AsyncMock, return_value=True):
        with patch('app.core.ai.ai_config.ai_config.generate_image',
                   new_callable=AsyncMock, return_value='https://example.com/good.jpg'):
            result = _run(svc._generate_single_image_with_seed(
                scene_id='scene_1', prompt='a cat', is_free=False
            ))

    assert result.image_url == 'https://example.com/good.jpg'
    assert result.scene_id == 'scene_1'
    # Seed should not have been bumped
    assert svc._book_seed == 42


# ── 2. Corrupt image triggers re-generation with bumped seed ────────────

def test_corrupt_image_retries_with_bumped_seed():
    """When validation fails, re-generate with a new seed and succeed on attempt 2."""
    svc = _make_image_service()

    # First call returns corrupt, second returns valid
    validate_side_effects = [False, True]
    generate_urls = ['https://example.com/corrupt.jpg', 'https://example.com/good.jpg']

    with patch.object(svc, '_validate_remote_image',
                      new_callable=AsyncMock, side_effect=validate_side_effects):
        with patch('app.core.ai.ai_config.ai_config.generate_image',
                   new_callable=AsyncMock, side_effect=generate_urls):
            result = _run(svc._generate_single_image_with_seed(
                scene_id='scene_1', prompt='a cat', is_free=False
            ))

    assert result.image_url == 'https://example.com/good.jpg'
    # Seed should have been bumped once (42 -> 43)
    assert svc._book_seed == 43


# ── 3. All attempts exhausted raises ValueError ─────────────────────────

def test_all_attempts_exhausted_returns_placeholder():
    """When all validation attempts fail, return a placeholder image (not crash)."""
    svc = _make_image_service()

    with patch.object(svc, '_validate_remote_image',
                      new_callable=AsyncMock, return_value=False):
        with patch('app.core.ai.ai_config.ai_config.generate_image',
                   new_callable=AsyncMock, return_value='https://example.com/corrupt.jpg'):
            result = _run(svc._generate_single_image_with_seed(
                scene_id='scene_1', prompt='a cat', is_free=False
            ))

    # Should return a placeholder image, not crash
    assert result.scene_id == 'scene_1'
    assert result.image_url.startswith('file://')
    assert 'placeholder' in result.image_url


# ── 4. API exception propagated on final attempt ────────────────────────

def test_api_exception_propagated():
    """When generate_image raises on every attempt, the exception propagates."""
    svc = _make_image_service()

    with patch('app.core.ai.ai_config.ai_config.generate_image',
               new_callable=AsyncMock, side_effect=Exception('Runware API error')):
        with pytest.raises(Exception, match='Runware API error'):
            _run(svc._generate_single_image_with_seed(
                scene_id='scene_1', prompt='a cat', is_free=False
            ))


# ── 5. None seed doesn't crash ──────────────────────────────────────────

def test_none_seed_no_crash():
    """When _book_seed is None, retries should work without crashing."""
    svc = _make_image_service()
    svc._book_seed = None

    validate_side_effects = [False, True]
    generate_urls = ['https://example.com/bad.jpg', 'https://example.com/good.jpg']

    with patch.object(svc, '_validate_remote_image',
                      new_callable=AsyncMock, side_effect=validate_side_effects):
        with patch('app.core.ai.ai_config.ai_config.generate_image',
                   new_callable=AsyncMock, side_effect=generate_urls):
            result = _run(svc._generate_single_image_with_seed(
                scene_id='scene_1', prompt='a cat', is_free=False
            ))

    assert result.image_url == 'https://example.com/good.jpg'
    assert svc._book_seed is None  # Should stay None, not get bumped
