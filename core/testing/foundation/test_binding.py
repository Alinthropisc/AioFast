from core.foundation import Binding, BindingType


class TestBinding:
    def test_transient_binding(self):
        b = Binding(abstract="key", concrete=str, binding_type=BindingType.TRANSIENT)
        assert not b.is_resolved
        assert not b.is_shared
        assert repr(b)

    def test_singleton_binding(self):
        b = Binding(abstract="key", concrete=str, binding_type=BindingType.SINGLETON)
        assert b.is_shared
        assert not b.is_resolved

    def test_instance_binding(self):
        obj = "hello"
        b = Binding(abstract="key", concrete=str, binding_type=BindingType.INSTANCE, instance=obj)
        assert b.is_shared
        assert b.is_resolved
        assert b.instance == "hello"

    def test_reset_singleton(self):
        b = Binding(abstract="key", concrete=str, binding_type=BindingType.SINGLETON, instance="cached")
        assert b.is_resolved
        b.reset()
        assert not b.is_resolved

    def test_reset_instance_no_effect(self):
        b = Binding(abstract="key", concrete=str, binding_type=BindingType.INSTANCE, instance="immutable")
        b.reset()
        assert b.is_resolved  # instance should NOT be reset

    def test_scoped_binding_not_shared(self):
        b = Binding(abstract="key", concrete=str, binding_type=BindingType.SCOPED)
        assert not b.is_shared

    def test_tags(self):
        b = Binding(abstract="key", concrete=str, binding_type=BindingType.TRANSIENT, tags={"logging", "core"})
        assert "logging" in b.tags
        assert "core" in b.tags
