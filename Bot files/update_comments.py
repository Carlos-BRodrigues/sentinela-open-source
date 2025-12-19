import json
import time
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

# Load Config
with open("config.json") as jsonfile:
    db_config = json.load(jsonfile)['database']

engine = create_engine(
    URL.create(
        db_config['drivername'],
        db_config['username'],
        db_config['password'],
        db_config['host'],
        db_config['port'],
        db_config['database']
    ),
    connect_args={'charset': 'utf8mb4', 'use_unicode': True},
    pool_size=10,
    max_overflow=20,
)

def update_comment_levels_sql():
    """
    1. Recursively updates comment levels for valid trees.
    2. Flags orphaned comments (deleted parents) as Level -2.
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Starting Level Update...")
    
    current_level = 1
    total_updated = 0
    
    # The Recursive Tree Builder
    while True:
        print(f"Processing Generation {current_level} -> {current_level + 1}...")
        
        # Finds children (-1) whose parents are (current_level) and promotes them.
        sql_query = text("""
            UPDATE telegram_comments c_child
            JOIN telegram_comments c_parent 
                ON c_child.reply_to_comment_id = c_parent.comment_id
                AND c_child.discussion_group_id = c_parent.discussion_group_id
            SET c_child.comment_level = :next_level
            WHERE c_parent.comment_level = :current_level
              AND c_child.comment_level = -1
        """)
        
        try:
            result = session.execute(sql_query, {
                'current_level': current_level, 
                'next_level': current_level + 1
            })
            session.commit()
            
            rows_affected = result.rowcount
            print(f"  -> Updated {rows_affected} comments to Level {current_level + 1}")
            
            if rows_affected == 0:
                print("No more children found. Tree traversal complete.")
                break
                
            total_updated += rows_affected
            current_level += 1
            
            if current_level > 200:
                print("[WARN] Reached Level 200. Stopping infinite loop protection.")
                break
                
        except Exception as e:
            print(f"[ERROR] Failed to update levels: {e}")
            session.rollback()
            break

    # Orphans
    print("Scanning for orphans - comments replying to deleted messages (or something else?)...")
    
    try:
        # Any comment still at -1 implies its parent was not found in the loop above.
        sql_orphan = text("""
            UPDATE telegram_comments 
            SET comment_level = -2 
            WHERE comment_level = -1
        """)
        
        result = session.execute(sql_orphan)
        session.commit()
        print(f"  -> Flagged {result.rowcount} comments as Orphans (Level -2).")
        
    except Exception as e:
        print(f"[ERROR] Failed to flag orphans: {e}")
        session.rollback()

    session.close()
    print(f"Done. Total valid tree updates: {total_updated}")

if __name__ == "__main__":
    start_time = time.time()
    update_comment_levels_sql()
    print(f"Execution time: {time.time() - start_time:.2f} seconds")
