"""
Database migration to add WHISPER tables.

This migration adds the new WHISPER reasoning chain tables alongside
existing tables without breaking any existing functionality.
"""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def migrate_to_whisper_schema(db_path: str = "gum.db"):
    """
    Add WHISPER tables to existing database schema.

    This migration is safe to run multiple times and won't affect existing data.
    """
    try:
        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            # Enable WAL mode for better concurrent access
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=30000")

            # Create WHISPER tables
            await create_whisper_tables(db)

            # Create indexes for performance
            await create_whisper_indexes(db)

            await db.commit()

        logger.info("✅ WHISPER database migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ WHISPER database migration failed: {e}")
        return False


async def create_whisper_tables(db):
    """Create all WHISPER-related tables."""

    # Session tracking table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS whisper_sessions (
            id TEXT PRIMARY KEY,
            trigger_proposition_id INTEGER REFERENCES propositions(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processing_time_seconds REAL,
            session_status TEXT DEFAULT 'in_progress',
            FOREIGN KEY (trigger_proposition_id) REFERENCES propositions(id) ON DELETE CASCADE
        )
    """)

    # Scenario understanding table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS scenario_understandings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES whisper_sessions(id),
            current_activity TEXT,
            immediate_context TEXT,
            accomplishment_goal TEXT,
            state_of_mind TEXT,
            challenges TEXT,  -- JSON array
            broader_context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES whisper_sessions(id) ON DELETE CASCADE
        )
    """)

    # Goal reasoning table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS goal_reasonings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES whisper_sessions(id),
            primary_goal TEXT,
            secondary_goals TEXT,  -- JSON array
            timeline TEXT,
            constraints TEXT,  -- JSON array
            skill_level TEXT,
            working_style TEXT,
            immediate_next_steps TEXT,  -- JSON array
            most_helpful TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES whisper_sessions(id) ON DELETE CASCADE
        )
    """)

    # Next move prediction table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS next_move_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES whisper_sessions(id),
            predicted_action TEXT,
            useful_preparation TEXT,
            specific_content TEXT,
            content_format TEXT,
            detail_level TEXT,
            time_saving TEXT,
            stuck_prevention TEXT,
            confidence_boost TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES whisper_sessions(id) ON DELETE CASCADE
        )
    """)

    # Delivery strategy table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS delivery_strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES whisper_sessions(id),
            delivery_type TEXT,
            message TEXT,
            content_type TEXT,
            specific_content TEXT,
            tone TEXT,
            positioning TEXT,
            button_text TEXT,
            engagement_strategy TEXT,
            safety_check TEXT,
            helpfulness_score REAL,
            timing_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES whisper_sessions(id) ON DELETE CASCADE
        )
    """)

    # Prepared content table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS prepared_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES whisper_sessions(id),
            content TEXT,
            content_type TEXT,
            completeness TEXT,
            production_ready BOOLEAN,
            includes_documentation BOOLEAN,
            includes_error_handling BOOLEAN,
            includes_logging BOOLEAN,
            usage_example TEXT,
            dependencies TEXT,  -- JSON array
            help_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES whisper_sessions(id) ON DELETE CASCADE
        )
    """)

    # Whisper UI data table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS whisper_ui_data (
            id TEXT PRIMARY KEY,
            session_id TEXT REFERENCES whisper_sessions(id),
            title TEXT,
            message TEXT,
            action_type TEXT,
            button_text TEXT,
            positioning TEXT,
            content TEXT,
            confidence REAL,
            helpfulness REAL,
            timing REAL,
            rationale TEXT,
            usage_example TEXT,
            dependencies TEXT,  -- JSON array
            delivered BOOLEAN DEFAULT FALSE,
            user_interaction TEXT,  -- 'viewed', 'used', 'dismissed'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES whisper_sessions(id) ON DELETE CASCADE
        )
    """)

    logger.info("Created all WHISPER tables")


async def create_whisper_indexes(db):
    """Create indexes for WHISPER table performance."""

    # Session indexes
    await db.execute("CREATE INDEX IF NOT EXISTS idx_whisper_sessions_proposition ON whisper_sessions(trigger_proposition_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_whisper_sessions_status ON whisper_sessions(session_status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_whisper_sessions_created ON whisper_sessions(created_at)")

    # Foreign key indexes for performance
    await db.execute("CREATE INDEX IF NOT EXISTS idx_scenario_session ON scenario_understandings(session_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_goals_session ON goal_reasonings(session_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_prediction_session ON next_move_predictions(session_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_strategy_session ON delivery_strategies(session_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_content_session ON prepared_contents(session_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ui_session ON whisper_ui_data(session_id)")

    # UI data indexes
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ui_delivered ON whisper_ui_data(delivered)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_ui_interaction ON whisper_ui_data(user_interaction)")

    logger.info("Created WHISPER performance indexes")


async def verify_migration(db_path: str = "gum.db"):
    """Verify that WHISPER tables were created successfully."""
    try:
        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            # Check if all tables exist
            tables = [
                'whisper_sessions',
                'scenario_understandings',
                'goal_reasonings',
                'next_move_predictions',
                'delivery_strategies',
                'prepared_contents',
                'whisper_ui_data'
            ]

            for table in tables:
                result = await db.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not await result.fetchone():
                    logger.error(f"❌ Table {table} was not created")
                    return False

            # Count existing data to ensure nothing was lost
            result = await db.execute("SELECT COUNT(*) FROM propositions")
            prop_count = (await result.fetchone())[0]

            result = await db.execute("SELECT COUNT(*) FROM observations")
            obs_count = (await result.fetchone())[0]

            logger.info(f"✅ Migration verified: {prop_count} propositions, {obs_count} observations preserved")
            return True

    except Exception as e:
        logger.error(f"❌ Migration verification failed: {e}")
        return False


async def rollback_whisper_migration(db_path: str = "gum.db"):
    """Rollback WHISPER migration by dropping new tables."""
    try:
        import aiosqlite

        async with aiosqlite.connect(db_path) as db:
            tables = [
                'whisper_ui_data',
                'prepared_contents',
                'delivery_strategies',
                'next_move_predictions',
                'goal_reasonings',
                'scenario_understandings',
                'whisper_sessions'
            ]

            for table in tables:
                try:
                    await db.execute(f"DROP TABLE IF EXISTS {table}")
                    logger.info(f"Dropped table {table}")
                except Exception as e:
                    logger.warning(f"Could not drop table {table}: {e}")

            await db.commit()

        logger.info("✅ WHISPER migration rolled back successfully")
        return True

    except Exception as e:
        logger.error(f"❌ WHISPER rollback failed: {e}")
        return False


# CLI interface for running migration
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WHISPER Database Migration")
    parser.add_argument("--db-path", default="gum.db", help="Path to database file")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration instead of applying")
    parser.add_argument("--verify", action="store_true", help="Only verify migration status")

    args = parser.parse_args()

    if args.verify:
        success = asyncio.run(verify_migration(args.db_path))
    elif args.rollback:
        success = asyncio.run(rollback_whisper_migration(args.db_path))
    else:
        success = asyncio.run(migrate_to_whisper_schema(args.db_path))

    exit(0 if success else 1)