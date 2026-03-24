import sys
sys.stdout.reconfigure(encoding='utf-8')
from database import get_engine
import sqlalchemy as sa

engine = get_engine()
with engine.connect() as conn:
    existing = [row[1] for row in conn.execute(sa.text('PRAGMA table_info(deliverable_reviews)')).fetchall()]
    print('Existing cols:', existing)
    new_cols = {
        'version': 'INTEGER DEFAULT 1',
        'checklist': 'TEXT',
        'ai_review_status': 'VARCHAR(50)',
        'ai_review_result': 'TEXT',
        'ai_reviewer_model': 'VARCHAR(100)',
        'human_comments': 'TEXT',
        'ai_overrides': 'TEXT',
    }
    for col, td in new_cols.items():
        if col not in existing:
            conn.execute(sa.text(f'ALTER TABLE deliverable_reviews ADD COLUMN {col} {td}'))
            print(f'Added: {col}')
    conn.commit()
    final = [row[1] for row in conn.execute(sa.text('PRAGMA table_info(deliverable_reviews)')).fetchall()]
    print('Final cols:', final)
print('Migration complete.')
