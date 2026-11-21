"""测试公共夹具：在临时数据目录中初始化 NoneBot2 并加载插件。"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

import pytest

_TEST_DATA = Path(tempfile.mkdtemp(prefix="pokemon-tests-"))
os.environ["POKEMON_DATA_DIR"] = str(_TEST_DATA)
os.environ["POKEMON_RESOURCE_AUTO_DOWNLOAD"] = "false"
os.environ["POKEMON_WEB_ENABLED"] = "true"

import nonebot  # noqa: E402

nonebot.init(driver="~fastapi", command_start={"/"}, superusers={"super-1"})

_PLUGIN = nonebot.load_plugin("nonebot_plugin_pokemon")
assert _PLUGIN is not None

from nonebot_plugin_pokemon.web.app import setup_web  # noqa: E402

setup_web()


@pytest.fixture(scope="session")
def fastapi_app():
    from nonebot import get_app

    return get_app()


@pytest.fixture(scope="session")
def client(fastapi_app):
    from fastapi.testclient import TestClient

    return TestClient(fastapi_app)


@pytest.fixture()
def uid() -> str:
    return f"user-{uuid.uuid4().hex[:10]}"


@pytest.fixture()
def headers(uid):
    return {"X-Pokemon-User": uid, "X-Pokemon-User-Name": "Tester"}
