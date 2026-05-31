import logging
import threading

from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer

from src.initial_setup import get_logger
from src.registry.registry import AgentRegistry

logger = get_logger(__name__)


class _RegistryFileHandler(FileSystemEventHandler):
    def __init__(self, registry: AgentRegistry, filename: str) -> None:
        self._registry = registry
        self._filename = filename

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return
        if event.src_path.endswith(self._filename):
            logger.info("Registry file changed, reloading...")
            self._registry.reload()


def start_registry_watcher(registry: AgentRegistry, registry_path: str) -> Observer:
    from pathlib import Path

    path = Path(registry_path).resolve()
    handler = _RegistryFileHandler(registry, path.name)
    observer = Observer()
    observer.schedule(handler, str(path.parent), recursive=False)
    observer.daemon = True
    observer.start()
    logger.info("Watching %s for changes", path)
    return observer
