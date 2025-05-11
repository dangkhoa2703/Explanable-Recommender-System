#!/bin/bash

SEED_FLAG="/app/.seeded"

if [ ! -f "$SEED_FLAG" ]; then
  echo "🚀 Running seed_data.py for the first time..."
  python seed_data.py && touch "$SEED_FLAG"
  echo "✅ Seeding complete."
else
  echo "⏭️ Skipping seeding — already done."
fi

echo "🚀 Starting Streamlit..."
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0
