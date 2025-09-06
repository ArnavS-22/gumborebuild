#!/usr/bin/env python3
"""
Test script for the Proactive Suggestion Engine

This script tests the new proactive suggestion engine by:
1. Creating a test observation with realistic transcription data
2. Triggering the proactive engine
3. Verifying suggestions are generated and saved
4. Testing the API endpoints
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_proactive_engine():
    """Test the proactive suggestion engine end-to-end."""
    
    try:
        # Import GUM components
        from gum.gum import gum
        from gum.observers import Observer
        from gum.schemas import Update
        
        logger.info("🧪 Starting Proactive Engine Test")
        
        # Initialize GUM instance
        logger.info("Initializing GUM instance...")
        gum_instance = gum(
            user_name="TestUser",
            model="gpt-4o",
            data_directory="~/.cache/gum",
            verbosity=logging.INFO
        )
        
        await gum_instance.connect_db()
        logger.info("✅ GUM instance connected")
        
        # Create a mock observer
        class TestObserver(Observer):
            def __init__(self):
                super().__init__("test_observer")
            
            async def _worker(self):
                pass
        
        observer = TestObserver()
        
        # Create realistic test transcription data - only what's actually visible
        test_transcription = """
        Application: Gmail
        Window Title: Inbox (47) - Gmail
        
        Visible Text Content:
        The user is looking at their Gmail inbox which shows 47 unread messages.
        The inbox displays a list of email subjects and senders.
        
        Current activity shows:
        - Gmail interface with inbox view
        - 47 unread message count displayed
        - List of emails with various subjects visible
        - No specific email content or sender details clearly visible
        
        The user appears to be browsing their email inbox.
        """
        
        # Create update with test data
        update = Update(
            content=test_transcription,
            content_type="input_text"
        )
        
        logger.info("📝 Created test observation with realistic transcription data")
        logger.info(f"Content preview: {test_transcription[:100]}...")
        
        # Process the update through GUM (this should trigger proactive suggestions)
        logger.info("🚀 Processing update through GUM (should trigger proactive engine)...")
        await gum_instance._default_handler(observer, update)
        
        # Wait a moment for async processing
        await asyncio.sleep(3)
        
        # Query the database to check if proactive suggestions were created
        logger.info("🔍 Checking database for proactive suggestions...")
        async with gum_instance._session() as session:
            from gum.models import Suggestion
            from sqlalchemy import select, desc
            
            # Get recent proactive suggestions
            stmt = select(Suggestion).where(
                Suggestion.category == "proactive"
            ).order_by(desc(Suggestion.created_at)).limit(5)
            
            result = await session.execute(stmt)
            proactive_suggestions = result.scalars().all()
            
            if proactive_suggestions:
                logger.info(f"✅ Found {len(proactive_suggestions)} proactive suggestions!")
                
                for i, suggestion in enumerate(proactive_suggestions, 1):
                    logger.info(f"  {i}. {suggestion.title}")
                    logger.info(f"     Description: {suggestion.description[:100]}...")
                    logger.info(f"     Category: {suggestion.category}")
                    logger.info(f"     Created: {suggestion.created_at}")
                    logger.info("")
            else:
                logger.warning("❌ No proactive suggestions found in database")
                
            # Also check for any recent observations
            from gum.models import Observation
            obs_stmt = select(Observation).order_by(desc(Observation.created_at)).limit(1)
            obs_result = await session.execute(obs_stmt)
            recent_obs = obs_result.scalar_one_or_none()
            
            if recent_obs:
                logger.info(f"✅ Recent observation found: ID {recent_obs.id}")
                logger.info(f"   Content preview: {recent_obs.content[:100]}...")
            else:
                logger.warning("❌ No recent observations found")
        
        logger.info("🧪 Proactive Engine Test Completed")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_api_endpoints():
    """Test the API endpoints for proactive suggestions."""
    
    try:
        import aiohttp
        
        logger.info("🌐 Testing API endpoints...")
        
        base_url = "http://localhost:8000"
        
        async with aiohttp.ClientSession() as session:
            # Test suggestion history endpoint
            logger.info("Testing /suggestions/history endpoint...")
            async with session.get(f"{base_url}/suggestions/history?limit=10") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Got {len(data)} suggestions from API")
                    
                    proactive_count = sum(1 for s in data if s.get('type') == 'proactive')
                    gumbo_count = len(data) - proactive_count
                    
                    logger.info(f"   Proactive: {proactive_count}, Gumbo: {gumbo_count}")
                else:
                    logger.error(f"❌ API request failed: {response.status}")
            
            # Test proactive-only filter
            logger.info("Testing proactive suggestions filter...")
            async with session.get(f"{base_url}/suggestions/history?suggestion_type=proactive&limit=5") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Got {len(data)} proactive suggestions")
                else:
                    logger.error(f"❌ Proactive filter failed: {response.status}")
            
            # Test stats endpoint
            logger.info("Testing /suggestions/stats endpoint...")
            async with session.get(f"{base_url}/suggestions/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Stats: {data.get('total_suggestions')} total")
                    logger.info(f"   Proactive: {data.get('proactive_suggestions')}")
                    logger.info(f"   Gumbo: {data.get('gumbo_suggestions')}")
                else:
                    logger.error(f"❌ Stats request failed: {response.status}")
            
            # Test proactive trigger endpoint
            logger.info("Testing /suggestions/test-proactive endpoint...")
            async with session.post(f"{base_url}/suggestions/test-proactive") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Proactive test trigger: {data.get('message')}")
                    if data.get('suggestions'):
                        logger.info(f"   Generated {data.get('suggestions_count')} suggestions")
                else:
                    logger.error(f"❌ Proactive trigger failed: {response.status}")
        
        logger.info("🌐 API endpoint testing completed")
        
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        logger.info("💡 Make sure the controller is running on localhost:8000")

if __name__ == "__main__":
    print("=" * 60)
    print(" PROACTIVE SUGGESTION ENGINE TEST")
    print("=" * 60)
    print()
    
    # Run the tests
    asyncio.run(test_proactive_engine())
    print()
    asyncio.run(test_api_endpoints())
    
    print()
    print("=" * 60)
    print(" TEST COMPLETED")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start the controller: python controller.py")
    print("2. Open the frontend and go to the Suggestions tab")
    print("3. Submit a text observation via /observations/text")
    print("4. Watch for immediate proactive suggestions!")