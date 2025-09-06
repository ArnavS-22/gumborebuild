#!/usr/bin/env python3
"""
Find propositions that actually have working observation relationships.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def find_working_propositions():
    """Find propositions that actually have observations."""
    
    try:
        from gum.gum import gum
        
        # Initialize GUM instance
        gum_instance = gum("TestUser", "gpt-4")
        await gum_instance.connect_db()
        
        async with gum_instance.Session() as session:
            from gum.models import Observation, Proposition, observation_proposition
            from sqlalchemy import select, text, func
            
            print("🔍 Finding propositions with actual observations...")
            
            # Get all propositions with their observation counts
            stmt = select(
                Proposition.id,
                Proposition.text,
                func.count(observation_proposition.c.observation_id).label('obs_count')
            ).outerjoin(
                observation_proposition, 
                Proposition.id == observation_proposition.c.proposition_id
            ).group_by(Proposition.id, Proposition.text).order_by(
                func.count(observation_proposition.c.observation_id).desc()
            ).limit(10)
            
            result = await session.execute(stmt)
            props_with_counts = result.fetchall()
            
            print(f"\n📊 Top 10 propositions by observation count:")
            for i, (prop_id, prop_text, obs_count) in enumerate(props_with_counts):
                print(f"   {i+1}. Prop {prop_id}: {obs_count} observations")
                print(f"      Text: {prop_text[:100]}...")
                
                if obs_count > 0:
                    # Get the actual observations for this proposition
                    stmt = select(Observation).join(
                        observation_proposition,
                        Observation.id == observation_proposition.c.observation_id
                    ).where(observation_proposition.c.proposition_id == prop_id)
                    
                    obs_result = await session.execute(stmt)
                    observations = obs_result.scalars().all()
                    
                    print(f"      Observations:")
                    for j, obs in enumerate(observations[:2]):  # Show first 2
                        print(f"        {j+1}. [{obs.content_type}] {obs.content[:80]}...")
                
                print()
            
            # Find propositions with exactly 1 observation (most likely to work)
            stmt = select(
                Proposition.id,
                Proposition.text
            ).join(
                observation_proposition,
                Proposition.id == observation_proposition.c.proposition_id
            ).group_by(Proposition.id, Proposition.text).having(
                func.count(observation_proposition.c.observation_id) == 1
            ).limit(5)
            
            result = await session.execute(stmt)
            single_obs_props = result.fetchall()
            
            print(f"\n🎯 Propositions with exactly 1 observation (best candidates):")
            for i, (prop_id, prop_text) in enumerate(single_obs_props):
                print(f"   {i+1}. Prop {prop_id}: {prop_text[:100]}...")
            
            print("\n✅ Analysis completed!")
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(find_working_propositions())
