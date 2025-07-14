# #!/usr/bin/env python3
# """
# Test psycopg with CockroachDB.
# """

# import logging
# import os
# import random
# import time
# import uuid
# from argparse import ArgumentParser, RawTextHelpFormatter

# import psycopg2
# from psycopg2.errors import SerializationFailure
# import psycopg2.extras
# from dotenv import load_dotenv

# load_dotenv()


# def create_accounts(conn):
#     psycopg2.extras.register_uuid()
#     ids = []
#     id1 = uuid.uuid4()
#     id2 = uuid.uuid4()
#     with conn.cursor() as cur:
#         cur.execute(
#             "CREATE TABLE IF NOT EXISTS accounts (id UUID PRIMARY KEY, balance INT)"
#         )
#         cur.execute(
#             "UPSERT INTO accounts (id, balance) VALUES (%s, 1000), (%s, 250)", (id1, id2))
#         logging.debug("create_accounts(): status message: %s",
#                       cur.statusmessage)
#     conn.commit()
#     ids.append(id1)
#     ids.append(id2)
#     return ids


# def delete_accounts(conn):
#     with conn.cursor() as cur:
#         cur.execute("DELETE FROM accounts")
#         logging.debug("delete_accounts(): status message: %s",
#                       cur.statusmessage)
#     conn.commit()


# def print_balances(conn):
#     with conn.cursor() as cur:
#         cur.execute("SELECT id, balance FROM accounts")
#         logging.debug("print_balances(): status message: %s",
#                       cur.statusmessage)
#         rows = cur.fetchall()
#         conn.commit()
#         print(f"Balances at {time.asctime()}:")
#         for row in rows:
#             print("account id: {0}  balance: ${1:2d}".format(row['id'], row['balance']))


# def transfer_funds(conn, frm, to, amount):
#     with conn.cursor() as cur:

#         # Check the current balance.
#         cur.execute("SELECT balance FROM accounts WHERE id = %s", (frm,))
#         from_balance = cur.fetchone()['balance']
#         if from_balance < amount:
#             raise RuntimeError(
#                 f"insufficient funds in {frm}: have {from_balance}, need {amount}"
#             )

#         # Perform the transfer.
#         cur.execute(
#             "UPDATE accounts SET balance = balance - %s WHERE id = %s", (
#                 amount, frm)
#         )
#         cur.execute(
#             "UPDATE accounts SET balance = balance + %s WHERE id = %s", (
#                 amount, to)
#         )

#     conn.commit()
#     logging.debug("transfer_funds(): status message: %s", cur.statusmessage)


# def run_transaction(conn, op, max_retries=3):
#     """
#     Execute the operation *op(conn)* retrying serialization failure.

#     If the database returns an error asking to retry the transaction, retry it
#     *max_retries* times before giving up (and propagate it).
#     """
#     # leaving this block the transaction will commit or rollback
#     # (if leaving with an exception)
#     with conn:
#         for retry in range(1, max_retries + 1):
#             try:
#                 op(conn)

#                 # If we reach this point, we were able to commit, so we break
#                 # from the retry loop.
#                 return

#             except SerializationFailure as e:
#                 # This is a retry error, so we roll back the current
#                 # transaction and sleep for a bit before retrying. The
#                 # sleep time increases for each failed transaction.
#                 logging.debug("got error: %s", e)
#                 conn.rollback()
#                 logging.debug("EXECUTE SERIALIZATION_FAILURE BRANCH")
#                 sleep_ms = (2**retry) * 0.1 * (random.random() + 0.5)
#                 logging.debug("Sleeping %s seconds", sleep_ms)
#                 time.sleep(sleep_ms)

#             except psycopg2.Error as e:
#                 logging.debug("got error: %s", e)
#                 logging.debug("EXECUTE NON-SERIALIZATION_FAILURE BRANCH")
#                 raise e

#         raise ValueError(
#             f"transaction did not succeed after {max_retries} retries")


# def main():
#     opt = parse_cmdline()
#     logging.basicConfig(level=logging.DEBUG if opt.verbose else logging.INFO)
#     try:
#         # Attempt to connect to cluster with connection string provided to
#         # script. By default, this script uses the value saved to the
#         # DATABASE_URL environment variable.
#         # For information on supported connection string formats, see
#         # https://www.cockroachlabs.com/docs/stable/connect-to-the-database.html.
#         db_url = opt.dsn
#         conn = psycopg2.connect(
#             db_url,
#             application_name="$ docs_simplecrud_psycopg2",
#             cursor_factory=psycopg2.extras.RealDictCursor,
#             **{
#                 "sslmode": "verify-ca",
#                 "sslrootcert": "/home/handeesofficial/backend/root.crt"
#             }
#         )
#     except Exception as e:
#         logging.fatal("database connection failed")
#         logging.fatal(e)
#         return
#     ids = create_accounts(conn)
#     print_balances(conn)

#     amount = 100
#     toId = ids.pop()
#     fromId = ids.pop()

#     try:
#         run_transaction(conn, lambda conn: transfer_funds(
#             conn, fromId, toId, amount))

#     except ValueError as ve:
#         # Below, we print the error and continue on so this example is easy to
#         # run (and run, and run...).  In real code you should handle this error
#         # and any others thrown by the database interaction.
#         logging.debug("run_transaction(conn, op) failed: %s", ve)
#         pass

#     print_balances(conn)

#     delete_accounts(conn)

#     # Close communication with the database.
#     conn.close()


# def parse_cmdline():
#     parser = ArgumentParser(description=__doc__,
#                             formatter_class=RawTextHelpFormatter)

#     parser.add_argument("-v", "--verbose",
#                         action="store_true", help="print debug info")

#     parser.add_argument(
#         "dsn",
#         default=os.environ.get("DATABASE_URL"),
#         nargs="?",
#         help="""\
# database connection string\
#  (default: value of the DATABASE_URL environment variable)
#             """,
#     )

#     opt = parser.parse_args()
#     if opt.dsn is None:
#         parser.error("database connection string not set")
#     return opt


# if __name__ == "__main__":
#     main()

import requests
import mimetypes
import os

def upload_file_with_presigned_url(presigned_url: str, file_path: str):
    """
    Uploads a file to Google Cloud Storage using a pre-signed URL.

    Args:
        presigned_url: The pre-signed URL generated by your backend.
        file_path: The local path to the file you want to upload.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    # Determine the content type (MIME type) of the file
    # This is crucial for GCS to correctly store the object.
    # It's best practice to include this when generating the pre-signed URL
    # and match it when uploading.
    content_type, _ = mimetypes.guess_type(file_path)
    file_size = os.path.getsize(file_path)
    print("file size is::", file_size)
    if content_type is None:
        content_type = 'application/octet-stream'

    try:
        with open(file_path, 'rb') as f:
            response = requests.put(presigned_url, data=f, headers={
                'Content-Type': content_type,
                'Content-Length': str(file_size)
            })

        response.raise_for_status()

        print(f"File '{file_path}' uploaded successfully!")
        print(f"GCS Response Status: {response.status_code}")
        print(response.text)
        print(f"GCS Response Content-Length header: {response.headers.get('Content-Length')}")
        print(f"GCS Response Content-Type header: {response.headers.get('Content-Type')}")
        # print(response.json())

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
        print(f"Response Body: {response.text}") # Print response body for debugging
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"An unexpected error occurred: {err}")
        print(err)
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    test_presigned_url = "https://storage.googleapis.com/handees_service_request_images_dev/cat.png?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=firebase-adminsdk-fbsvc%40handees-dev.iam.gserviceaccount.com%2F20250708%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20250708T005612Z&X-Goog-Expires=900&X-Goog-SignedHeaders=content-type%3Bhost&X-Goog-Signature=44eb06c9dba5738fab7051745607992b80bbb13ca3a88dce37170f97427e9f1cb732417e84d6e79526b6d98b3d417d568410753f04436f128adf4acafaac19e1e21bb3d915cd308de5dcc24c4df30b52d4ca2fcab624d8617de79b5cb2e45e9050d3765e44d3616ce83efe6e839a79caead86e9276ba67bc83fd84c586056ece38f24b60bfb92ac7ff9dcecae0ba683a312ba60440dc91d7a4d378570e1c73613c6174f5545056b2c64ed2f6fe456cc8f6f3fcc1162689c085e5827448366c40fa07d811de318b73b1e39001b5ab41f60fd1d6478bee2c9691c6fa99e736c91a539035f76588db9cbebff5d5c10ff4091a82f6c0b3f75b16d4b4e8e058df3fdc"

    # 2. Replace with the path to a local file you want to upload
    test_file_path = "cat.png"

    # Create a dummy file for testing if it doesn't exist
    if not os.path.exists(test_file_path):
        with open(test_file_path, 'wb') as f:
            f.write(b'This is dummy image data.')
        print(f"Created dummy file: {test_file_path}")

    upload_file_with_presigned_url(test_presigned_url, test_file_path)

    # --- Important Notes ---
    # 1. Content-Type: Ensure the 'Content-Type' header sent with the PUT request
    #    matches the content type specified (if any) when the pre-signed URL was generated.
    #    If they don't match, GCS might reject the upload or store it with the wrong type.
    # 2. Method: Always use a PUT request for uploads to pre-signed URLs.
    # 3. Expiration: Pre-signed URLs have a limited lifespan. Ensure you use them before they expire.
    # 4. Error Handling: The `requests.raise_for_status()` will catch common HTTP errors.
    #    Inspect `response.text` for more specific GCS error messages if an upload fails.