from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import event as sa_event

logger = logging.getLogger(__name__)


class ModelObserver:
    """
    Model lifecycle observer — like Laravel's Observer.

    Usage:
        class UserObserver(ModelObserver):
            def creating(self, instance):
                instance.slug = slugify(instance.name)

            def created(self, instance):
                logger.info("User created: %s", instance.id)

            def deleting(self, instance):
                if instance.is_admin:
                    raise ValueError("Cannot delete admin!")

        ObserverRegistry.observe(User, UserObserver())
    """

    def creating(self, instance: Any) -> None:
        """Before INSERT."""

    def created(self, instance: Any) -> None:
        """After INSERT."""

    def updating(self, instance: Any) -> None:
        """Before UPDATE."""

    def updated(self, instance: Any) -> None:
        """After UPDATE."""

    def deleting(self, instance: Any) -> None:
        """Before DELETE."""

    def deleted(self, instance: Any) -> None:
        """After DELETE."""

    def saving(self, instance: Any) -> None:
        """Before INSERT or UPDATE."""

    def saved(self, instance: Any) -> None:
        """After INSERT or UPDATE."""


class ObserverRegistry:
    """
    Central registry for model observers.
    Hooks into SQLAlchemy mapper events automatically.

    Usage:
        ObserverRegistry.observe(User, UserObserver())
        ObserverRegistry.observe(User, AuditObserver())

        # Or with decorator:
        @observe(User)
        class UserObserver(ModelObserver):
            ...
    """

    _observers: dict[type, list[ModelObserver]] = {}
    _registered: set = set()

    @classmethod
    def observe(cls, model: type, observer: ModelObserver) -> None:
        """Register an observer for a model class."""
        if model not in cls._observers:
            cls._observers[model] = []
        cls._observers[model].append(observer)

        # Setup SQLAlchemy events once per model
        if model not in cls._registered:
            cls._setup_events(model)
            cls._registered.add(model)
        logger.debug("Registered %s for %s", observer.__class__.__name__, model.__name__)

    @classmethod
    def _setup_events(cls, model: type) -> None:
        """Wire SQLAlchemy mapper events to observer methods."""

        @sa_event.listens_for(model, "before_insert")
        def _before_insert(mapper, connection, target):
            for obs in cls._observers.get(model, []):
                obs.saving(target)
                obs.creating(target)

        @sa_event.listens_for(model, "after_insert")
        def _after_insert(mapper, connection, target):
            for obs in cls._observers.get(model, []):
                obs.created(target)
                obs.saved(target)

        @sa_event.listens_for(model, "before_update")
        def _before_update(mapper, connection, target):
            for obs in cls._observers.get(model, []):
                obs.saving(target)
                obs.updating(target)

        @sa_event.listens_for(model, "after_update")
        def _after_update(mapper, connection, target):
            for obs in cls._observers.get(model, []):
                obs.updated(target)
                obs.saved(target)

        @sa_event.listens_for(model, "before_delete")
        def _before_delete(mapper, connection, target):
            for obs in cls._observers.get(model, []):
                obs.deleting(target)

        @sa_event.listens_for(model, "after_delete")
        def _after_delete(mapper, connection, target):
            for obs in cls._observers.get(model, []):
                obs.deleted(target)

    @classmethod
    def get_observers(cls, model: type) -> list[ModelObserver]:
        return cls._observers.get(model, [])

    @classmethod
    def clear(cls) -> None:
        """Clear observers (SQLAlchemy hooks stay but become no-op)."""
        cls._observers.clear()
        # НЕ чистим _registered — иначе дублируются event listeners


def observe(*models: type):
    """
    Decorator to register observer.

    Usage:
        @observe(User)
        class UserObserver(ModelObserver):
            def creating(self, instance):
                ...
    """

    def decorator(observer_class: type[ModelObserver]):
        instance = observer_class()
        for model in models:
            ObserverRegistry.observe(model, instance)
        return observer_class

    return decorator
