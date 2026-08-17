import pytest


@pytest.mark.asyncio
async def test_get_users_for_scheduling():
    from app.core.newsletter.user_prefs_service import get_users_for_scheduling

    users = await get_users_for_scheduling(60)
    assert isinstance(users, list)
    assert all(isinstance(user, dict) for user in users)
