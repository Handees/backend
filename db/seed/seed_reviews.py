import pandas as pd
import random
from datetime import datetime

# 1. Load Data
bookings_df = pd.read_csv("Handees_bookings.csv")
valid_bookings = bookings_df.dropna(subset=["booking_id", "customer_id", "artisan_id"])

# 2. Map Artisan ID to their underlying User ID
# Assuming you have a CSV or database export of your artisans table to map artisan_id -> user_id
try:
    artisans_df = pd.read_csv("Handees_artisan.csv") 
    # Create a dictionary mapping: { 'artisan_id': 'user_id' }
    artisan_to_user_map = pd.Series(artisans_df.user_id.values, index=artisans_df.artisan_id).to_dict()
    print(artisan_to_user_map)
except FileNotFoundError:
    print("Warning: Handees_artisans.csv not found. Make sure you have a way to map artisan_id to user_id.")
    # Fallback: if artisan_id and user_id share the exact same UUID in your schema, 
    # you could technically bypass the map, but a lookup map is the safest relational approach.
    artisan_to_user_map = {}

# 3. Rich Comment Libraries
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
    ]
}

sql_statements = []

print(f"Generating rich reviews for {len(valid_bookings)} bookings...")
idx = 1

for _, row in valid_bookings.iterrows():
    booking_id = row["booking_id"]
    customer_id = row["customer_id"] # This is the customer's user_id
    artisan_id = row["artisan_id"]
    created_at = row.get("created_at", datetime.now())

    # --- 1. Review FOR Artisan (Written by Customer) ---
    # Target: artisan_id | Commenter: customer_id (Valid User ID)
    w_art = int(row["artisan_rating"]) if pd.notna(row.get("artisan_rating")) else random.randint(0, 5)
    if w_art not in comments_artisan:
        w_art = 5
    c_art = random.choice(comments_artisan[w_art]).replace("'", "''")

    sql_1 = (
        f"INSERT INTO reviews (id, weight, comment, user_id, artisan_id, commenter_id, booking_id, created_at, updated_at) "
        f"VALUES ({idx}, {w_art}, '{c_art}', NULL, '{artisan_id}', '{customer_id}', '{booking_id}', '{created_at}', '{created_at}');"
    )
    sql_statements.append(sql_1)
    idx += 1

    # --- 2. Review FOR Customer (Written by Artisan) ---
    # Target: user_id (the customer) | Commenter: The Artisan's underlying User ID
    
    # Look up the artisan's user_id from our mapping dictionary
    # (If your artisan_id and user_id are identical in your schema, you can just use artisan_id here instead)
    artisan_user_id = artisan_to_user_map.get(artisan_id, None)
    
    # If we couldn't find a mapping but your schema uses the same UUID for both tables, fallback to:
    # artisan_user_id = artisan_id 

    if artisan_user_id:
        w_cust = int(row["customer_rating"]) if pd.notna(row.get("customer_rating")) else random.randint(0, 5)
        if w_cust not in comments_customer:
            w_cust = 5
        c_cust = random.choice(comments_customer[w_cust]).replace("'", "''")
        if artisan_user_id == customer_id:
            choices = [x for x in artisan_to_user_map.values() if x.lower() != artisan_user_id.lower()]
            print(artisan_user_id, choices)
            artisan_user_id = random.choice(choices)
        sql_2 = (
            f"INSERT INTO reviews (id, weight, comment, user_id, artisan_id, commenter_id, booking_id, created_at, updated_at) "
            f"VALUES ({idx}, {w_cust}, '{c_cust}', '{customer_id}', NULL, '{artisan_user_id}', '{booking_id}', '{created_at}', '{created_at}');"
        )
        sql_statements.append(sql_2)
        idx += 1

# Save
with open("seed_reviews.sql", "w") as f:
    f.write("\n".join(sql_statements))

print("Done. Check seed_reviews.sql")