"""
Connection Manager Service - Handles database connections for Integration feature
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Optional, Dict, Any, Tuple
import time

from app.models.datasource import DataSource

# Set up logging
logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages database connections for Integration ETL operations"""
    
    def __init__(self):
        self._connection_pools = {}  # datasource_id -> engine mapping
        self.max_pool_size = 5
        self.pool_timeout = 30
        self.connection_timeout = 10
        
    def get_engine(self, datasource_id: int):
        """Get SQLAlchemy engine for datasource (with connection pooling)"""
        if datasource_id in self._connection_pools:
            return self._connection_pools[datasource_id]
        
        datasource = DataSource.query.get(datasource_id)
        if not datasource:
            raise ValueError(f"DataSource {datasource_id} not found")
        
        if not datasource.is_active:
            raise ValueError(f"DataSource {datasource.name} is not active")
        
        try:
            # Create engine with connection pooling
            engine = create_engine(
                datasource.connection_string,
                poolclass=QueuePool,
                pool_size=self.max_pool_size,
                max_overflow=10,
                pool_timeout=self.pool_timeout,
                connect_args={
                    'timeout': self.connection_timeout,
                    'check_same_thread': False  # For SQLite compatibility if needed
                },
                echo=False  # Set to True for SQL debugging
            )
            
            # Test connection
            with engine.connect() as conn:
                if datasource.db_type == 'oracle':
                    conn.execute(text("SELECT 1 FROM DUAL"))
                else:  # postgres
                    conn.execute(text("SELECT 1"))
            
            # Store in pool cache
            self._connection_pools[datasource_id] = engine
            logger.info(f"Created connection pool for DataSource {datasource.name}")
            
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create connection pool for DataSource {datasource.name}: {e}")
            raise ConnectionError(f"Cannot connect to {datasource.name}: {str(e)}")
    
    @contextmanager
    def get_connection(self, datasource_id: int):
        """Get database connection with automatic cleanup"""
        engine = self.get_engine(datasource_id)
        connection = None
        
        try:
            connection = engine.connect()
            logger.debug(f"Opened connection to DataSource {datasource_id}")
            yield connection
            
        except Exception as e:
            logger.error(f"Connection error for DataSource {datasource_id}: {e}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise
            
        finally:
            if connection:
                try:
                    connection.close()
                    logger.debug(f"Closed connection to DataSource {datasource_id}")
                except:
                    pass
    
    def execute_query(self, datasource_id: int, query: str, params: Dict[str, Any] = None) -> Tuple[list, int]:
        """
        Execute SQL query and return results with row count
        
        Args:
            datasource_id: DataSource ID
            query: SQL query to execute
            params: Query parameters (optional)
            
        Returns:
            Tuple of (results_list, row_count)
        """
        start_time = time.time()
        
        with self.get_connection(datasource_id) as conn:
            try:
                # Execute query
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                
                # Fetch results for SELECT queries
                if query.strip().upper().startswith('SELECT'):
                    rows = result.fetchall()
                    
                    # Convert to list of dictionaries
                    results = []
                    if rows:
                        columns = result.keys()
                        results = [dict(zip(columns, row)) for row in rows]
                    
                    execution_time = time.time() - start_time
                    logger.info(f"Query executed successfully: {len(results)} rows in {execution_time:.2f}s")
                    
                    return results, len(results)
                    
                else:
                    # For INSERT/UPDATE/DELETE queries
                    conn.commit()
                    rows_affected = result.rowcount
                    
                    execution_time = time.time() - start_time
                    logger.info(f"Query executed successfully: {rows_affected} rows affected in {execution_time:.2f}s")
                    
                    return [], rows_affected
                    
            except Exception as e:
                conn.rollback()
                execution_time = time.time() - start_time
                logger.error(f"Query execution failed after {execution_time:.2f}s: {e}")
                raise
    
    def test_connection(self, datasource_id: int) -> Tuple[bool, str]:
        """Test connection to datasource"""
        try:
            datasource = DataSource.query.get(datasource_id)
            if not datasource:
                return False, "DataSource not found"
            
            with self.get_connection(datasource_id) as conn:
                if datasource.db_type == 'oracle':
                    result = conn.execute(text("SELECT 'OK' as status FROM DUAL"))
                else:  # postgres
                    result = conn.execute(text("SELECT 'OK' as status"))
                
                row = result.fetchone()
                if row and row[0] == 'OK':
                    return True, "Connection successful"
                else:
                    return False, "Unexpected test result"
                    
        except Exception as e:
            logger.error(f"Connection test failed for DataSource {datasource_id}: {e}")
            return False, str(e)
    
    def validate_query(self, query: str, query_type: str = 'extract') -> Tuple[bool, list]:
        """
        Validate SQL query for security and correctness
        
        Args:
            query: SQL query to validate
            query_type: 'extract' or 'load'
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        query_upper = query.strip().upper()
        
        if not query.strip():
            errors.append("Query cannot be empty")
            return False, errors
        
        if query_type == 'extract':
            # Extract queries should be SELECT only
            if not query_upper.startswith('SELECT'):
                errors.append("Extract queries must start with SELECT")
            
            # Check for dangerous operations
            dangerous_ops = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 'TRUNCATE', 'EXECUTE']
            for op in dangerous_ops:
                if op in query_upper:
                    errors.append(f"Extract queries cannot contain {op} operations")
        
        elif query_type == 'load':
            # Load queries should be INSERT, UPDATE, MERGE, or UPSERT
            valid_starts = ['INSERT', 'UPDATE', 'MERGE', 'UPSERT']
            if not any(query_upper.startswith(op) for op in valid_starts):
                errors.append("Load queries must start with INSERT, UPDATE, MERGE, or UPSERT")
            
            # Check for dangerous operations
            dangerous_ops = ['DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'EXECUTE']
            for op in dangerous_ops:
                if op in query_upper:
                    errors.append(f"Load queries cannot contain {op} operations")
        
        # Check for SQL injection patterns
        injection_patterns = ['--', '/*', '*/', ';--', 'xp_', 'sp_']
        for pattern in injection_patterns:
            if pattern in query.lower():
                errors.append(f"Query contains potentially unsafe pattern: {pattern}")
        
        return len(errors) == 0, errors
    
    def get_table_info(self, datasource_id: int, table_name: str) -> Dict[str, Any]:
        """Get table structure information"""
        try:
            datasource = DataSource.query.get(datasource_id)
            if not datasource:
                raise ValueError(f"DataSource {datasource_id} not found")
            
            if datasource.db_type == 'oracle':
                query = """
                SELECT column_name, data_type, nullable, data_default
                FROM all_tab_columns 
                WHERE table_name = UPPER(:table_name)
                AND owner = USER
                ORDER BY column_id
                """
            else:  # postgres
                query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = LOWER(:table_name)
                ORDER BY ordinal_position
                """
            
            results, _ = self.execute_query(datasource_id, query, {'table_name': table_name})
            
            return {
                'table_name': table_name,
                'columns': results,
                'column_count': len(results)
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {'table_name': table_name, 'columns': [], 'error': str(e)}
    
    def close_all_connections(self):
        """Close all connection pools (cleanup)"""
        for datasource_id, engine in self._connection_pools.items():
            try:
                engine.dispose()
                logger.info(f"Closed connection pool for DataSource {datasource_id}")
            except Exception as e:
                logger.error(f"Error closing connection pool for DataSource {datasource_id}: {e}")
        
        self._connection_pools.clear()
    
    def get_connection_stats(self) -> Dict[int, Dict[str, Any]]:
        """Get connection pool statistics"""
        stats = {}
        
        for datasource_id, engine in self._connection_pools.items():
            pool = engine.pool
            stats[datasource_id] = {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalidated': pool.invalidated()
            }
        
        return stats

# Global connection manager instance
connection_manager = ConnectionManager()