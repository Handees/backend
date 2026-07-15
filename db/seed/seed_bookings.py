import pandas as pd
import random
import uuid
from datetime import datetime

# --- Configuration ---
CSV_FILE = "booking.csv"
TARGET_CUSTOMER = 'YVFr9oGC9CPpwBriJ3QbIW1PcO23'
TARGET_ARTISAN = 'f5e29d05737548b6b739618cb3c4d37f'
TARGET_TOTAL = 3

SETTLEMENT_TYPES = ['NEGOTIATION', 'HOURLY_RATE']
PAYMENT_METHODS = ['CASH', 'CARD']
DEFAULT_CATEGORY = '1065941583869181953'

# 1. Load Data and Find Matches
df = pd.read_csv(CSV_FILE)
matching_bookings = df[df['customer_id'] == TARGET_CUSTOMER]

num_existing = len(matching_bookings)
num_to_update = min(num_existing, TARGET_TOTAL)
num_to_create = TARGET_TOTAL - num_to_update

print(f"Found {num_existing} existing bookings for customer.")
print(f"Plan: Generate {num_to_update} UPDATEs and {num_to_create} INSERTs.")

sql_statements = []

# 2. Generate UPDATE Statements
if num_to_update > 0:
    bookings_to_update = matching_bookings.sample(n=num_to_update)
    for _, row in bookings_to_update.iterrows():
        b_id = row['booking_id']
        s_type = random.choice(SETTLEMENT_TYPES)
        p_meth = random.choice(PAYMENT_METHODS)
        
        sql = (
            f"UPDATE booking \n"
            f"SET status = 'IN_PROGRESS', \n"
            f"    settlement_type = '{s_type}', \n"
            f"    payment_method = '{p_meth}', \n"
            f"    artisan_id = '{TARGET_ARTISAN}', \n"
            f"    updated_at = NOW() \n"
            f"WHERE booking_id = '{b_id}';"
        )
        sql_statements.append(sql)

# 3. Generate INSERT Statements
for _ in range(num_to_create):
    b_id = uuid.uuid4().hex
    s_type = random.choice(SETTLEMENT_TYPES)
    p_meth = random.choice(PAYMENT_METHODS)
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    location = "ST_GeomFromText('POINT(6.517073 3.385310)')"
    
    sql = (
        f"INSERT INTO booking (\n"
        f"    booking_id, customer_id, artisan_id, category_id, \n"
        f"    status, settlement_type, payment_method, location, \n"
        f"    created_at, updated_at, clock_in_flag, details_confirmed\n"
        f") VALUES (\n"
        f"    '{b_id}', '{TARGET_CUSTOMER}', '{TARGET_ARTISAN}', '{DEFAULT_CATEGORY}', \n"
        f"    'IN_PROGRESS', '{s_type}', '{p_meth}', {location}, \n"
        f"    '{created_at}', '{created_at}', false, false\n"
        f");"
    )
    sql_statements.append(sql)

# 4. Save to File
output_file = 'seed_bookings_smart_update.sql'
with open(output_file, 'w') as f:
    f.write('\n\n'.join(sql_statements))

print(f"Done! SQL statements written to '{output_file}'.")