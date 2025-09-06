#!/usr/bin/env python3
"""
Debug script to check database contents.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def debug_database():
    """Check what's actually in the database."""
    
    try:
        from gum.gum import gum
        
        # Initialize GUM instance
        gum_instance = gum("TestUser", "gpt-4")
        await gum_instance.connect_db()
        
        async with gum_instance.Session() as session:
            from gum.models import Observation, Proposition, observation_proposition
            from sqlalchemy import select, text
            
            print("🔍 Checking database contents...")
            
            # Check observations table
            stmt = select(Observation).limit(5)
            result = await session.execute(stmt)
            observations = result.scalars().all()
            
            print(f"\n📋 Observations table: {len(observations)} records")
            for i, obs in enumerate(observations):
                print(f"   Obs {i+1}: ID={obs.id}, Type={obs.content_type}, Content={obs.content[:100]}...")
            
            # Check propositions table
            stmt = select(Proposition).limit(5)
            result = await session.execute(stmt)
            propositions = result.scalars().all()
            
            print(f"\n📋 Propositions table: {len(propositions)} records")
            for i, prop in enumerate(propositions):
                print(f"   Prop {i+1}: ID={prop.id}, Text={prop.text[:100]}...")
            
            # Check junction table
            stmt = select(observation_proposition).limit(10)
            result = await session.execute(stmt)
            relationships = result.fetchall()
            
            print(f"\n🔗 Junction table: {len(relationships)} relationships")
            for i, rel in enumerate(relationships):
                print(f"   Rel {i+1}: obs_id={rel.observation_id}, prop_id={rel.proposition_id}")
            
            # Check if specific propositions have observations
            if propositions:
                test_prop = propositions[0]
                print(f"\n🧪 Testing proposition {test_prop.id}...")
                
                # Direct query to junction table
                stmt = select(observation_proposition).where(observation_proposition.c.proposition_id == test_prop.id)
                result = await session.execute(stmt)
                direct_rels = result.fetchall()
                
                print(f"   Direct junction query: {len(direct_rels)} relationships")
                for rel in direct_rels:
                    print(f"     obs_id={rel.observation_id}")
                
                # Check if observations exist
                if direct_rels:
                    obs_ids = [rel.observation_id for rel in direct_rels]
                    stmt = select(Observation).where(Observation.id.in_(obs_ids))
                    result = await session.execute(stmt)
                    actual_obs = result.scalars().all()
                    
                    print(f"   Actual observations found: {len(actual_obs)}")
                    for obs in actual_obs:
                        print(f"     [{obs.content_type}] {obs.content[:100]}...")
            
            print("\n✅ Database debug completed!")
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_database())
