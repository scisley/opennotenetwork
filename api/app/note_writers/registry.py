"""
Note Writer Registry

Central registry for all note writers. Similar to fact checker registry.
"""

from typing import Any, Optional

import structlog

from .base import BaseNoteWriter

logger = structlog.get_logger()


class NoteWriterRegistry:
    """Registry for managing note writers"""

    _writers: dict[str, type[BaseNoteWriter]] = {}
    _instances: dict[str, BaseNoteWriter] = {}

    @classmethod
    def register(cls, writer_class: type[BaseNoteWriter]) -> None:
        """
        Register a note writer class

        Args:
            writer_class: The note writer class to register
        """
        # Create an instance to get the slug
        instance = writer_class()
        slug = instance.slug

        if slug in cls._writers:
            logger.warning(f"Note writer {slug} already registered, overwriting")

        cls._writers[slug] = writer_class
        cls._instances[slug] = instance
        logger.info(f"Registered note writer: {slug}")

    @classmethod
    def get_class(cls, slug: str) -> Optional[type[BaseNoteWriter]]:
        """
        Get a note writer class by slug

        Args:
            slug: The note writer slug

        Returns:
            The note writer class or None if not found
        """
        return cls._writers.get(slug)

    @classmethod
    def get_instance(cls, slug: str) -> Optional[BaseNoteWriter]:
        """
        Get a note writer instance by slug

        Args:
            slug: The note writer slug

        Returns:
            The note writer instance or None if not found
        """
        if slug not in cls._instances and slug in cls._writers:
            cls._instances[slug] = cls._writers[slug]()
        return cls._instances.get(slug)

    @classmethod
    def list_all(cls) -> list[dict[str, Any]]:
        """
        List all registered note writers

        Returns:
            List of note writer information
        """
        writers = []
        for slug, instance in cls._instances.items():
            writers.append({
                "slug": slug,
                "name": instance.name,
                "description": instance.description,
                "version": instance.version,
                "platforms": instance.platforms,
                "configuration": instance.get_configuration()
            })
        return writers

    @classmethod
    def list_for_platform(cls, platform_id: str) -> list[dict[str, Any]]:
        """
        List note writers that support a specific platform

        Args:
            platform_id: The platform ID to filter by

        Returns:
            List of note writer information for the platform
        """
        writers = []
        for slug, instance in cls._instances.items():
            if platform_id in instance.platforms:
                writers.append({
                    "slug": slug,
                    "name": instance.name,
                    "description": instance.description,
                    "version": instance.version,
                    "platforms": instance.platforms,
                    "configuration": instance.get_configuration()
                })
        return writers


def register_note_writer(writer_class: type[BaseNoteWriter]):
    """
    Decorator to automatically register note writers

    Usage:
        @register_note_writer
        class MyNoteWriter(BaseNoteWriter):
            ...
    """
    NoteWriterRegistry.register(writer_class)
    return writer_class
