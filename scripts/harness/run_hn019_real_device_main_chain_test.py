#!/usr/bin/env python3
"""Tests for run_hn019_real_device_main_chain.py."""

from __future__ import annotations

import unittest

import run_hn019_real_device_main_chain as hn019


class HN019RealDeviceMainChainTests(unittest.TestCase):
    def test_wait_for_health_uses_no_proxy_opener(self) -> None:
        opened: list[tuple[str, int]] = []
        proxy_handlers: list[_FakeProxyHandler] = []
        original_build_opener = hn019.build_opener
        original_proxy_handler = hn019.ProxyHandler
        try:
            hn019.ProxyHandler = _FakeProxyHandler
            hn019.build_opener = lambda handler: _FakeOpener(handler, opened, proxy_handlers)

            hn019._wait_for_health("http://192.168.2.15:8000/v1", timeout_seconds=1)

            self.assertEqual(opened, [("http://192.168.2.15:8000/healthz", 3)])
            self.assertEqual([handler.proxies for handler in proxy_handlers], [{}])
        finally:
            hn019.build_opener = original_build_opener
            hn019.ProxyHandler = original_proxy_handler


class _FakeProxyHandler:
    def __init__(self, proxies: dict[str, str]) -> None:
        self.proxies = proxies


class _FakeOpener:
    def __init__(
        self,
        handler: _FakeProxyHandler,
        opened: list[tuple[str, int]],
        proxy_handlers: list[_FakeProxyHandler],
    ) -> None:
        self._opened = opened
        proxy_handlers.append(handler)

    def open(self, url: str, *, timeout: int) -> "_FakeResponse":
        self._opened.append((url, timeout))
        return _FakeResponse()


class _FakeResponse:
    status = 200

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
