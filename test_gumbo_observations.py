#!/usr/bin/env python3
"""
Test script to verify Gumbo engine observation retrieval.
This tests whether propositions are actually coming back with their observation data.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gum.services.gumbo_engine import get_gumbo_engine
from gum.models import Proposition, Observation
from gum.db_utils import search_propositions_bm25
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_observation_retrieval():
    """Test if propositions are being retrieved with their observations."""
    
    try:
        # Get a Gumbo engine instance
        engine = await get_gumbo_engine()
        logger.info("✅ Gumbo engine initialized")
        
        # Get a database session through the gum instance
        from gum.gum import gum
        gum_instance = gum("TestUser", "gpt-4")
        await gum_instance.connect_db()
        
        async with gum_instance.Session() as session:
            logger.info("✅ Database session created")
            
            # Test 1: Check if we have any propositions
            stmt = select(Proposition).order_by(desc(Proposition.created_at)).limit(5)
            result = await session.execute(stmt)
            propositions = result.scalars().all()
            
            if not propositions:
                logger.warning("⚠️ No propositions found in database")
                return
            
            logger.info(f"✅ Found {len(propositions)} recent propositions")
            
            # Test 2: Check if propositions have observations loaded
            for i, prop in enumerate(propositions):
                logger.info(f"\n📋 Proposition {i+1}:")
                logger.info(f"   ID: {prop.id}")
                logger.info(f"   Text: {prop.text[:100]}...")
                logger.info(f"   Has observations attribute: {hasattr(prop, 'observations')}")
                
                if hasattr(prop, 'observations'):
                    logger.info(f"   Observations loaded: {len(prop.observations) if prop.observations else 0}")
                    if prop.observations:
                        for j, obs in enumerate(list(prop.observations)[:3]):  # Show first 3
                            logger.info(f"     Obs {j+1}: [{obs.content_type}] {obs.content[:100]}...")
                else:
                    logger.warning("   ❌ No observations attribute found")
            
            # Test 3: Test the actual BM25 search with observations
            # Use a proposition that actually has observations (from our analysis)
            test_prop_id = 279  # This proposition has 5 observations
            stmt = select(Proposition).where(Proposition.id == test_prop_id)
            result = await session.execute(stmt)
            test_prop = result.scalar_one()
            
            if test_prop:
                logger.info(f"\n🔍 Testing BM25 search for proposition: {test_prop.text[:100]}...")
                
                # Test search with observations included
                search_results = await search_propositions_bm25(
                    session,
                    test_prop.text[:50],  # Use first 50 chars as query
                    limit=3,
                    include_observations=True,
                    enable_mmr=True,
                    enable_decay=True
                )
                
                logger.info(f"✅ BM25 search returned {len(search_results)} results")
                
                for i, (prop, score) in enumerate(search_results):
                    logger.info(f"\n   Result {i+1} (score: {score:.3f}):")
                    logger.info(f"     ID: {prop.id}")
                    logger.info(f"     Text: {prop.text[:100]}...")
                    logger.info(f"     Has observations: {hasattr(prop, 'observations')}")
                    
                    if hasattr(prop, 'observations') and prop.observations:
                        obs_count = len(prop.observations)
                        logger.info(f"     Observations count: {obs_count}")
                        
                        # Show first observation content
                        first_obs = list(prop.observations)[0]
                        logger.info(f"     First obs: [{first_obs.content_type}] {first_obs.content[:100]}...")
                    else:
                        logger.warning("     ❌ No observations found")
            
            # Test 4: Test the contextual retrieval method directly
            logger.info(f"\n🧪 Testing Gumbo's contextual retrieval method...")
            
            # Use the same proposition that has observations
            if test_prop:
                context_result = await engine._contextual_retrieval(session, test_prop)
            
            logger.info(f"✅ Contextual retrieval completed")
            logger.info(f"   Related propositions: {len(context_result.related_propositions)}")
            logger.info(f"   Total observations: {len(context_result.all_observations)}")
            
            if context_result.all_observations:
                total_content = sum(len(obs.get('content', '')) for obs in context_result.all_observations)
                logger.info(f"   Total observation content: {total_content} characters")
                
                # Show sample observations
                for i, obs in enumerate(context_result.all_observations[:3]):
                    logger.info(f"   Sample obs {i+1}: [{obs.get('content_type', 'unknown')}] {obs.get('content', '')[:100]}...")
            else:
                logger.warning("   ❌ No observations in context result")
            
            logger.info("\n✅ Test completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_database_relationships():
    """Test the database relationships directly."""
    
    try:
        from gum.gum import gum
        
        gum_instance = gum("TestUser", "gpt-4")
        await gum_instance.connect_db()
        
        async with gum_instance.Session() as session:
            logger.info("\n🔍 Testing database relationships directly...")
            
            # Test 1: Check observation_proposition table
            from gum.models import observation_proposition
            stmt = select(observation_proposition).limit(5)
            result = await session.execute(stmt)
            relationships = result.fetchall()
            
            logger.info(f"✅ Found {len(relationships)} observation-proposition relationships")
            
            for i, rel in enumerate(relationships):
                logger.info(f"   Relationship {i+1}: obs_id={rel.observation_id}, prop_id={rel.proposition_id}")
            
            # Test 2: Check if we can load observations with propositions
            stmt = (
                select(Proposition)
                .options(selectinload(Proposition.observations))
                .order_by(desc(Proposition.created_at))
                .limit(3)
            )
            
            result = await session.execute(stmt)
            propositions_with_obs = result.scalars().all()
            
            logger.info(f"✅ Loaded {len(propositions_with_obs)} propositions with observations")
            
            for i, prop in enumerate(propositions_with_obs):
                logger.info(f"   Prop {i+1}: {prop.text[:50]}...")
                logger.info(f"     Observations: {len(prop.observations)}")
                
                for j, obs in enumerate(list(prop.observations)[:2]):
                    logger.info(f"       Obs {j+1}: [{obs.content_type}] {obs.content[:80]}...")
            
            logger.info("✅ Database relationship test completed!")
            
    except Exception as e:
        logger.error(f"❌ Database relationship test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests."""
    logger.info("🚀 Starting Gumbo observation retrieval tests...")
    
    await test_database_relationships()
    await test_observation_retrieval()
    
    logger.info("🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
