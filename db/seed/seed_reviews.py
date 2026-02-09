import pandas as pd
import random
import uuid
from datetime import datetime

# 1. Load Data
bookings_df = pd.read_csv("Handees_bookings.csv")
valid_bookings = bookings_df.dropna(subset=["booking_id", "customer_id", "artisan_id"])

# 2. Rich Comment Libraries
comments_artisan = {
    5: [
        "Excellent craftsmanship! He fixed the piping issue in less than an hour.",
        "Honestly, I was surprised by how professional he was. Arrived 10 minutes early.",
        "The best artisan I've used on this app so far. Highly recommended.",
        "Very polite and respectful. He even cleaned up the workspace.",
        "Perfect execution. The finishing was top-notch.",
    ],
    4: [
        "Good job overall, but he arrived a bit late. The work itself was solid.",
        "He knows his stuff. Fixed the electrical fault quickly.",
        "Solid work. I'm satisfied with the result.",
        "Professional guy. Did exactly what was asked.",
        "Good experience. Will likely hire him again.",
    ],
    3: [
        "He tried his best, but the finishing could be better.",
        "Average service. He came late and didn't really apologize.",
        "Okay experience. Communication was a bit difficult.",
        "The work was just okay.",
    ],
    2: [
        "Not very satisfied. He rushed the job and left a mess.",
        "He didn't have the right tools and had to go back to get them.",
        "The repair didn't last two days.",
    ],
    1: [
        "Terrible experience. He was rude and unprofessional.",
        "Complete waste of time and money.",
        "I strongly advise against using this artisan.",
    ],
}

comments_customer = {
    5: [
        "Great client! Paid immediately after the job was completed.",
        "Very polite and provided a conducive environment.",
        "Excellent customer. Clear instructions.",
        "Hassle-free transaction. She even offered water.",
        "One of the best clients I've met.",
    ],
    4: [
        "Good client. Communication was clear, and payment was prompt.",
        "Nice person to work for. A bit strict, but fair.",
        "Good experience. Would definitely work for him again.",
    ],
    3: [
        "Okay client. Kept me waiting at the gate for 20 minutes.",
        "Payment was delayed slightly, but eventually received.",
        "A bit difficult to please.",
    ],
    2: [
        "Rude behavior. Was shouting over small details.",
        "Refused to pay the agreed amount initially.",
    ],
    1: [
        "Do not work for this person. Very hostile environment.",
        "Refused to pay after I completed the job.",
    ],
}

sql_statements = []

print(f"Generating rich reviews for {len(valid_bookings)} bookings...")
idx = 1

for _, row in valid_bookings.iterrows():
    booking_id = row["booking_id"]
    customer_id = row["customer_id"]
    artisan_id = row["artisan_id"]
    created_at = row.get("created_at", datetime.now())

    # --- 1. Review FOR Artisan ---
    # We explicitly set user_id to NULL
    w_art = int(row["artisan_rating"]) if pd.notna(row.get("artisan_rating")) else 5
    if w_art not in comments_artisan:
        w_art = 5
    c_art = random.choice(comments_artisan[w_art]).replace("'", "''")

    sql_1 = (
        f"INSERT INTO reviews (id, weight, comment, user_id, artisan_id, booking_id, created_at, updated_at) "
        f"VALUES ({idx}, {w_art}, '{c_art}', NULL, '{artisan_id}', '{booking_id}', '{created_at}', '{created_at}');"
    )
    sql_statements.append(sql_1)
    idx += 1

    # --- 2. Review FOR Customer ---
    # We explicitly set artisan_id to NULL
    w_cust = int(row["customer_rating"]) if pd.notna(row.get("customer_rating")) else 5
    if w_cust not in comments_customer:
        w_cust = 5
    c_cust = random.choice(comments_customer[w_cust]).replace("'", "''")

    sql_2 = (
        f"INSERT INTO reviews (id, weight, comment, user_id, artisan_id, booking_id, created_at, updated_at) "
        f"VALUES ({idx}, {w_cust}, '{c_cust}', '{customer_id}', NULL, '{booking_id}', '{created_at}', '{created_at}');"
    )
    sql_statements.append(sql_2)
    idx += 1

# Save
with open("seed_reviews.sql", "w") as f:
    f.write("\n".join(sql_statements))

print("Done. Check seed_reviews_fixed.sql")
