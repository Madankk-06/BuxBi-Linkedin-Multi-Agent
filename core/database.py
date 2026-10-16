import os
import logging
import sqlite3
import pymysql
import pymysql.cursors
from typing import Optional, Any
from .config import config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.is_sqlite = (config.DB_TYPE == "sqlite")
        self.init_db()

    def get_connection(self):
        """Get database connection (MySQL or SQLite)."""
        if self.is_sqlite:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(config.SQLITE_PATH), timeout=20)
            conn.row_factory = sqlite3.Row
            return conn
        else:
            try:
                return pymysql.connect(
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    database=config.DB_NAME,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True
                )
            except Exception as e:
                logger.warning(f"MySQL unavailable ({e}). Falling back to SQLite.")
                self.is_sqlite = True
                return self.get_connection()

    def init_db(self):
        """Initialize database tables."""
        if not self.is_sqlite:
            # 1. Attempt MySQL database creation
            try:
                temp_conn = pymysql.connect(
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    charset="utf8mb4"
                )
                with temp_conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                temp_conn.close()
            except Exception as e:
                logger.warning(f"Notice connecting to MySQL root server: {e}. Switching to SQLite.")
                self.is_sqlite = True

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if self.is_sqlite:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS posts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            topic TEXT NOT NULL,
                            hook_formula TEXT,
                            draft_text TEXT NOT NULL,
                            image_url TEXT,
                            status TEXT DEFAULT 'pending_approval',
                            scheduled_time TEXT,
                            post_urn TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS connections (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            person_name TEXT NOT NULL,
                            title TEXT,
                            company TEXT,
                            profile_url TEXT NOT NULL UNIQUE,
                            why_relevant TEXT,
                            customized_note TEXT NOT NULL,
                            status TEXT DEFAULT 'recommended',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS trends (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            source TEXT,
                            title TEXT NOT NULL,
                            url TEXT UNIQUE,
                            summary TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    conn.commit()
                    logger.info("SQLite database initialized successfully.")
                else:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS posts (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            topic VARCHAR(500) NOT NULL,
                            hook_formula VARCHAR(100),
                            draft_text TEXT NOT NULL,
                            image_url VARCHAR(500),
                            status VARCHAR(50) DEFAULT 'pending_approval',
                            scheduled_time VARCHAR(50),
                            post_urn VARCHAR(255),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS connections (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            person_name VARCHAR(255) NOT NULL,
                            title VARCHAR(255),
                            company VARCHAR(255),
                            profile_url VARCHAR(500) NOT NULL UNIQUE,
                            why_relevant TEXT,
                            customized_note VARCHAR(500) NOT NULL,
                            status VARCHAR(50) DEFAULT 'recommended',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS trends (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            source VARCHAR(100),
                            title VARCHAR(500) NOT NULL,
                            url VARCHAR(500) UNIQUE,
                            summary TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """)
                    logger.info("MySQL database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")
            raise

    def _prep_query(self, query: str) -> str:
        return query.replace("%s", "?") if self.is_sqlite else query

    # --- Post Operations ---
    def save_post_draft(self, topic: str, hook_formula: str, draft_text: str, image_url: Optional[str] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = self._prep_query("""
                INSERT INTO posts (topic, hook_formula, draft_text, image_url, status)
                VALUES (%s, %s, %s, %s, 'pending_approval')
            """)
            cursor.execute(query, (topic, hook_formula, draft_text, image_url))
            if self.is_sqlite:
                conn.commit()
                return cursor.lastrowid
            return cursor.lastrowid

    def update_post_status(self, post_id: int, status: str, scheduled_time: Optional[str] = None, post_urn: Optional[str] = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = self._prep_query("""
                UPDATE posts 
                SET status = %s, 
                    scheduled_time = COALESCE(%s, scheduled_time), 
                    post_urn = COALESCE(%s, post_urn)
                WHERE id = %s
            """)
            cursor.execute(query, (status, scheduled_time, post_urn, post_id))
            if self.is_sqlite:
                conn.commit()

    def get_post(self, post_id: int) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = self._prep_query("SELECT * FROM posts WHERE id = %s")
            cursor.execute(query, (post_id,))
            row = cursor.fetchone()
            return dict(row) if (row and self.is_sqlite) else row

    def get_latest_pending_post(self) -> Optional[dict]:
        """Fetch the most recent post draft awaiting approval."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts WHERE status = 'pending_approval' ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if (row and self.is_sqlite) else row

    def update_post_image(self, post_id: int, image_url: str):
        """Update the image attached to a post."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = self._prep_query("UPDATE posts SET image_url = %s WHERE id = %s")
            cursor.execute(query, (image_url, post_id))
            if self.is_sqlite:
                conn.commit()

    # --- Connection Operations ---
    def save_connection_lead(self, person_name: str, title: str, company: str, 
                             profile_url: str, why_relevant: str, customized_note: str) -> Optional[int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                query = self._prep_query("""
                    INSERT INTO connections (person_name, title, company, profile_url, why_relevant, customized_note)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """)
                cursor.execute(query, (person_name, title, company, profile_url, why_relevant, customized_note))
                if self.is_sqlite:
                    conn.commit()
                return cursor.lastrowid
            except (pymysql.IntegrityError, sqlite3.IntegrityError):
                return None

    def get_pending_connections(self, limit: int = 5) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = self._prep_query("SELECT * FROM connections WHERE status = 'recommended' ORDER BY id DESC LIMIT %s")
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows] if self.is_sqlite else rows

    # --- Trend Operations ---
    def save_trend(self, source: str, title: str, url: str, summary: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                query = self._prep_query("""
                    INSERT INTO trends (source, title, url, summary)
                    VALUES (%s, %s, %s, %s)
                """)
                cursor.execute(query, (source, title, url, summary))
                if self.is_sqlite:
                    conn.commit()
            except (pymysql.IntegrityError, sqlite3.IntegrityError):
                pass

db = Database()
