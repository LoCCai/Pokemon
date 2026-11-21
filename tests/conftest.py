"""测试公共夹具：在临时数据目录中初始化 NoneBot2 并加载插件。

离线测试不连真实宿主。这里把 ``tests/qweb_stub.py`` 装成
``src.qi_web.dependencies``，因此插件仍然走真实的“导入宿主依赖”路径。
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

_TEST_DATA = Path(tempfile.mkdtemp(prefix="pokemon-tests-"))
os.environ["POKEMON_DATA_DIR"] = str(_TEST_DATA)
os.environ["POKEMON_RESOURCE_AUTO_DOWNLOAD"] = "false"
os.environ["POKEMON_WEB_ENABLED"] = "true"

import qweb_stub  # noqa: E402

qweb_stub.install()

import nonebot  # noqa: E402

nonebot.init(driver="~fastapi", command_start={"/"}, superusers={"super-1"})

_PLUGIN = nonebot.load_plugin("nonebot_plugin_pokemon")
assert _PLUGIN is not None

from nonebot_plugin_pokemon.web.app import setup_web  # noqa: E402

assert setup_web() is True


@pytest.fixture(scope="session")
def fastapi_app():
    from nonebot import get_app

    return get_app()


@pytest.fixture(scope="session")
def client(fastapi_app):
    from fastapi.testclient import TestClient

    # Keep one ASGI event loop alive for commands that outlive the POST request.
    client = TestClient(fastapi_app)
    with client._portal_factory() as portal:
        client.portal = portal
        try:
            yield client
        finally:
            client.portal = None
            client.close()


@pytest.fixture()
def uid() -> str:
    return f"user-{uuid.uuid4().hex[:10]}"


@pytest.fixture()
def headers(uid):
    return {"X-Test-Account": f"member:{uid}", "X-CSRF-Token": qweb_stub.CSRF_TOKEN}


@pytest.fixture()
def admin_headers(uid):
    return {"X-Test-Account": f"admin:{uid}", "X-CSRF-Token": qweb_stub.CSRF_TOKEN}


@pytest.fixture()
def csrf_token():
    return qweb_stub.CSRF_TOKEN
