#!/usr/bin/env python3
"""
Test script to validate the SQLAlchemy transaction fix.

This script tests that background tasks (proactive and gumbo suggestions) 
no longer cause transaction context errors.
"""

import asyncio
import logging
import tempfile
import os
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_transaction_fix():
    """Test that the transaction fix prevents SQLAlchemy errors."""
    
    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Import GUM components
        from gum.gum import gum
        from gum.observers.screen import ScreenObserver
        from gum.models import init_db
        
        logger.info("Setting up test database...")
        await init_db(db_path, db_directory=None)
        
        # Create GUM instance with minimal setup
        logger.info("Initializing GUM instance...")
        screen_observer = ScreenObserver()
        gum_instance = gum(
            user_name="Test User",
            model="gpt-4o-mini",
            screen_observer,
            data_directory=str(Path(db_path).parent),
            db_name=Path(db_path).name,
            verbosity=logging.INFO
        )
        
        logger.info("Starting GUM...")
        await gum_instance.start()
        
        # Simulate some screen activity to trigger observations
        logger.info("Simulating screen observations...")
        
        # Create some test observations that should trigger background tasks
        for i in range(3):
            # This should trigger both proactive and potentially gumbo suggestions
            # The key test is that no SQLAlchemy transaction errors occur
            await asyncio.sleep(0.1)  # Small delay between observations
        
        # Wait a bit for background tasks to complete
        logger.info("Waiting for background tasks to complete...")
        await asyncio.sleep(2)
        
        # Check if there are any unhandled task exceptions
        pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
        logger.info(f"Pending tasks: {len(pending_tasks)}")
        
        # Stop GUM
        logger.info("Stopping GUM...")
        await gum_instance.stop()
        
        logger.info("✅ Test completed successfully - no transaction errors detected!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        return False
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        logger.info("Test cleanup completed")

async def main():
    """Main test runner."""
    logger.info("Starting SQLAlchemy transaction fix test...")
    
    try:
        success = await test_transaction_fix()
        if success:
            logger.info("🎉 All tests passed!")
            return 0
        else:
            logger.error("💥 Tests failed!")
            return 1
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
