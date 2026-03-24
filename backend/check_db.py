import sqlite3

conn = sqlite3.connect('apprelic.db')
c = conn.cursor()

# Update stuck in-progress to failed
c.execute("UPDATE analysis_results SET status='failed', error_message='Marked as failed due to being stuck in-progress' WHERE status='in-progress'")
updated_count = c.rowcount
conn.commit()
print(f"Updated {updated_count} stuck in-progress records to failed")

print("\nAll analyses by status:")
c.execute("SELECT status, COUNT(*) FROM analysis_results GROUP BY status")
for r in c.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
