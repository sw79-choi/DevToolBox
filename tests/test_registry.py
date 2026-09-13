# -*- coding: utf-8 -*-
"""Every shipped tool must register cleanly."""
from devtoolbox.core.plugin import ToolPlugin
from devtoolbox.core.registry import discover


def test_all_tools_load_without_errors():
    plugins, errors = discover()
    assert errors == [], [(e.module, e.message) for e in errors]
    assert len(plugins) >= 4


def test_tool_ids_are_unique_and_meta_is_complete():
    plugins, _ = discover()
    ids = [p.meta.id for p in plugins]
    assert len(ids) == len(set(ids))
    for plugin in plugins:
        assert isinstance(plugin, ToolPlugin)
        assert plugin.meta.id and plugin.meta.title and plugin.meta.category


def test_pdf_merger_is_in_the_document_category():
    plugins, _ = discover()
    merger = next(p for p in plugins if p.meta.id == "pdf_merger")
    assert merger.meta.category == "Document"


def test_plugins_are_sorted_by_order():
    plugins, _ = discover()
    orders = [p.meta.order for p in plugins]
    assert orders == sorted(orders)


def test_setting_keys_do_not_collide_within_a_tool():
    plugins, _ = discover()
    for plugin in plugins:
        keys = [f.key for f in plugin.settings_schema()]
        assert len(keys) == len(set(keys)), plugin.meta.id
