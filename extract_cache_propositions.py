#!/usr/bin/env python3
"""
Extract 1/6th of every proposition from the cache database.
"""

import sqlite3
import json
import os
from datetime import datetime

def extract_proposition_sample():
    """Extract 1/6th of every proposition from the cache database."""
    
    # Path to the cache database
    cache_db_path = os.path.expanduser("~/.cache/gum/gum.db")
    
    if not os.path.exists(cache_db_path):
        print(f"❌ Cache database not found: {cache_db_path}")
        return
    
    try:
        conn = sqlite3.connect(cache_db_path)
        cursor = conn.cursor()
        
        print("🔍 Extracting 1/6th of all propositions from cache database...")
        
        # Get total count of propositions
        cursor.execute("SELECT COUNT(*) FROM propositions")
        total_count = cursor.fetchone()[0]
        
        print(f"📊 Total propositions in cache database: {total_count}")
        
        # Calculate 1/6th (rounded up to ensure we get at least some data)
        sample_size = max(1, (total_count + 5) // 6)  # Round up
        print(f"🎯 Extracting {sample_size} propositions (1/6th of {total_count})")
        
        # Get a random sample of propositions with all their details
        query = """
        SELECT 
            id, text, reasoning, confidence, decay, 
            created_at, updated_at, revision_group, version
        FROM propositions 
        ORDER BY RANDOM() 
        LIMIT ?
        """
        
        cursor.execute(query, (sample_size,))
        propositions = cursor.fetchall()
        
        print(f"\n✅ Successfully extracted {len(propositions)} propositions:")
        print("=" * 80)
        
        # Display the propositions
        propositions_data = []
        for i, prop in enumerate(propositions, 1):
            prop_id, text, reasoning, confidence, decay, created_at, updated_at, revision_group, version = prop
            
            print(f"\n{i}. Proposition ID: {prop_id}")
            print(f"   Text: {text}")
            print(f"   Reasoning: {reasoning}")
            print(f"   Confidence: {confidence}")
            print(f"   Decay: {decay}")
            print(f"   Created: {created_at}")
            print(f"   Updated: {updated_at}")
            print(f"   Revision Group: {revision_group}")
            print(f"   Version: {version}")
            
            # Get related observations count
            cursor.execute("""
                SELECT COUNT(*) FROM observation_proposition 
                WHERE proposition_id = ?
            """, (prop_id,))
            obs_count = cursor.fetchone()[0]
            print(f"   Related Observations: {obs_count}")
            
            # Get parent propositions count
            cursor.execute("""
                SELECT COUNT(*) FROM proposition_parent 
                WHERE child_id = ?
            """, (prop_id,))
            parent_count = cursor.fetchone()[0]
            print(f"   Parent Propositions: {parent_count}")
            
            # Get child propositions count
            cursor.execute("""
                SELECT COUNT(*) FROM proposition_parent 
                WHERE parent_id = ?
            """, (prop_id,))
            child_count = cursor.fetchone()[0]
            print(f"   Child Propositions: {child_count}")
            
            # Store proposition data
            prop_data = {
                "id": prop_id,
                "text": text,
                "reasoning": reasoning,
                "confidence": confidence,
                "decay": decay,
                "created_at": created_at,
                "updated_at": updated_at,
                "revision_group": revision_group,
                "version": version,
                "related_observations_count": obs_count,
                "parent_propositions_count": parent_count,
                "child_propositions_count": child_count
            }
            propositions_data.append(prop_data)
            
            print("-" * 60)
        
        # Save to JSON file for easy access
        output_file = f"cache_propositions_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "extraction_info": {
                    "source_database": cache_db_path,
                    "total_propositions": total_count,
                    "sample_size": len(propositions),
                    "extraction_ratio": f"1/6th",
                    "extracted_at": datetime.now().isoformat()
                },
                "propositions": propositions_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Sample saved to: {output_file}")
        print(f"📈 Extraction complete: {len(propositions)}/{total_count} propositions")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    extract_proposition_sample()
