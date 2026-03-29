#!/bin/sh
set -e

echo "⏳ Initialising database..."
python -c "
from app import app, db, seed_demo_teacher
with app.app_context():
    db.create_all()
    seed_demo_teacher()
    print('✅ Database ready.')
"

echo "🚀 Starting app..."
exec "$@"