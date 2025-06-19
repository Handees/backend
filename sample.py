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
    if content_type is None:
        content_type = 'application/octet-stream' # Default if type can't be guessed

    print(f"Uploading {file_path} with Content-Type: {content_type}")
    # print(f"To pre-signed URL: {presigned_url}")

    try:
        with open(file_path, 'rb') as f:
            # Use requests.put for uploading.
            # The 'data' parameter takes the file-like object.
            # The 'headers' must include 'Content-Type'.
            response = requests.put(presigned_url, data=f, headers={
                'Content-Type': content_type
            })

        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        print(f"File '{file_path}' uploaded successfully!")
        print(f"GCS Response Status: {response.status_code}")

    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
        print(f"Response Body: {response.text}") # Print response body for debugging
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        print(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        print(f"An unexpected error occurred: {err}")
    except Exception as e:
        print(f"An error occurred: {e}")

# --- How to use it ---

if __name__ == "__main__":
    # 1. Replace with an actual pre-signed URL obtained from your backend
    # This URL would typically come from an API call to your server.
    # For a quick test, you might generate one manually or via gcloud CLI if permitted.
    # Example (replace with your actual URL):
    # This URL is just a placeholder example, it won't work.
    test_presigned_url = "https://storage.googleapis.com/handees_service_request_images_dev/test.css?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=firebase-adminsdk-fbsvc%40handees-dev.iam.gserviceaccount.com%2F20250619%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20250619T011217Z&X-Goog-Expires=900&X-Goog-SignedHeaders=content-type%3Bhost&X-Goog-Signature=0051185bb43165b9113b9e30a98ca7f9086f14377381fe0db1799c2a7d1167505ace08cab6c16bb5054765f14c01ea55a3c569358f8e79b36b691e7defb4ae92cb5d51ab9b340f6602c2dc05d1826cab1c70b417b931fa20faef4f7ec92dc5dfa1e7b8cdf005a65cb0347cd8ee7f5853404299dc5cd8ea75c7ebf2633759dfdde441a680252e4f588de4cccfbdfd8645fe6787f632cbc38b0e76cd3d36759652fefd8cd04490cc1d8dc54535c45378332869aadd3ae4526ba75a8f12e5d9dd53092c3be020ff777b0d3bac846b7b1d50dac887e898b191bd4f04b3ee2a8f28bd6a9959861d2b2479c797ac647a4c29125b5ec34e89d80a0722cff4b9e41328ee"

    # 2. Replace with the path to a local file you want to upload
    test_file_path = "test.css" # Make sure this file exists!

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