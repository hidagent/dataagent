"""Session and message store factory."""

from typing import Literal

from dataagent_core.session.store import SessionStore
from dataagent_core.session.message_store import MessageStore
from dataagent_core.session.stores.memory import MemorySessionStore
from dataagent_core.session.stores.memory_message import MemoryMessageStore


class SessionStoreFactory:
    """Factory for creating session store instances.
    
    Supports creating different storage backends based on configuration.
    """
    
    @staticmethod
    def create(
        store_type: Literal["memory", "mysql"],
        **kwargs,
    ) -> SessionStore:
        """Create a session store instance.
        
        Args:
            store_type: Type of store to create ("memory" or "mysql").
            **kwargs: Additional arguments for the store constructor.
                For MySQL: url, pool_size, max_overflow, pool_recycle
                
        Returns:
            SessionStore instance.
            
        Raises:
            ValueError: If store_type is not supported.
        """
        if store_type == "memory":
            return MemorySessionStore()
        elif store_type == "mysql":
            from dataagent_core.session.stores.mysql import MySQLSessionStore
            return MySQLSessionStore(
                url=kwargs["url"],
                pool_size=kwargs.get("pool_size", 10),
                max_overflow=kwargs.get("max_overflow", 20),
                pool_recycle=kwargs.get("pool_recycle", 3600),
            )
        else:
            raise ValueError(f"Unknown store type: {store_type}")


class MessageStoreFactory:
    """Factory for creating message store instances.
    
    Supports creating different storage backends based on configuration.
    """
    
    @staticmethod
    def create(
        store_type: Literal["memory", "mysql"],
        **kwargs,
    ) -> MessageStore:
        """Create a message store instance.
        
        Args:
            store_type: Type of store to create ("memory" or "mysql").
            **kwargs: Additional arguments for the store constructor.
                For MySQL: engine (SQLAlchemy AsyncEngine)
                
        Returns:
            MessageStore instance.
            
        Raises:
            ValueError: If store_type is not supported.
        """
        if store_type == "memory":
            return MemoryMessageStore()
        elif store_type == "mysql":
            from dataagent_core.session.stores.mysql_message import MySQLMessageStore
            if "engine" not in kwargs:
                raise ValueError("MySQL message store requires 'engine' argument")
            return MySQLMessageStore(engine=kwargs["engine"])
        else:
            raise ValueError(f"Unknown store type: {store_type}")
