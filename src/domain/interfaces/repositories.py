# src/domain/interfaces/repositories.py
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar, Any

# Generic type: T will be replaced by a real entity (e.g., Incident, Server)
T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """
    Base repository interface.
    Defines the standard CRUD operations for any domain entity.
    """

    @abstractmethod
    async def save(self, entity: T) -> T:
        """
        Save or update an entity.
        Returns the saved entity (with any generated fields like ID).
        """
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: Any) -> Optional[T]:
        """
        Retrieve an entity by its unique ID.
        Returns None if not found.
        """
        pass

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Retrieve a list of entities with pagination.
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: Any) -> bool:
        """
        Delete an entity by ID.
        Returns True if deleted, False if not found.
        """
        pass

"""
Summary
A short, abstract Python class with 4 methods. No logic – just a promise. Later, we'll write PostgresIncidentRepository that implements this interface for real database work.

Why This File?
Think of a repository as a drawer where you store and retrieve things (like incidents, servers, policies).

This file just says:
"Every drawer must have these 4 actions: save, get by ID, get all, and delete."

It doesn't care how the drawer works (PostgreSQL, a JSON file, or memory). That's the job of the Infrastructure layer later. This file is just the contract (promise) that all drawers must follow.

What Problem Does It Solve?
Stops you from writing database logic inside your business rules.

Makes it easy to swap databases later (e.g., switch from Postgres to MongoDB) without changing any business code.

Forces consistency – every repository works the same way.

Where does it live?
Folder: src/domain/interfaces/

File: repositories.py

Why this folder?
The Domain layer defines the rules. The Infrastructure layer follows them. This file is the rulebook for data storage.

Future files that depend on this:
All application services (they use the repository via this interface).

All infrastructure repository implementations (they must implement these methods).
"""