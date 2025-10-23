"""
Note Writers Module

This module contains all note writer implementations.
Each note writer should be registered with the registry.
"""

from .base import BaseNoteWriter, NoteResult
from .registry import NoteWriterRegistry, register_note_writer

# Import all note writer implementations to register them
from .x_note_writer_v1 import XNoteWriterV1

__all__ = [
    "BaseNoteWriter",
    "NoteResult",
    "NoteWriterRegistry",
    "register_note_writer",
    "XNoteWriterV1"
]
