import datetime
import requests
import hashlib
import hmac
import os
import geoip2.database

from models.signin_attempt import SignInAttempts
from flask import request
from loguru import logger
from user_agents import parse
from core import db
from add_extensions import (
    redis_,
    redis_2,
    redis_4,
    redis_7
)


import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def generate_device_hash():
    try:
        user_agent = parse(request.headers.get("User-Agent", ""))

        device_mac = (
            request.headers.get("X-Device-ID", "")
            .strip()
            .lower()
        )
    
        print("Device MAC:", device_mac, flush=True)

        device_name = (
            request.headers.get("X-Device-Model", "")
            .strip()
            .lower()
        )
        device_name = device_name if device_name else user_agent.device.family.strip().lower()
        print("Device Name:", device_name, flush=True)

        device_os = (
            request.headers.get("X-OS-Family")
            or user_agent.os.family
        ).strip().lower()

        if device_os.startswith("android"):
            device_os = "android"
        elif device_os.startswith("ios"):
            device_os = "ios"

        print("Device OS:", device_os, flush=True)

        server_secret = os.getenv("DEVICE_HASH_SECRET")

        if not server_secret:
            raise RuntimeError("DEVICE_HASH_SECRET is not configured.")

        raw = f"{device_mac}|{device_name}|{device_os}"

        device_hash = hmac.new(
            server_secret.encode(),
            raw.encode(),
            hashlib.sha256
        ).hexdigest()

        device_data = {
            "device_uuid": device_mac,
            "device_model": device_name,
            "device_os": device_os
        }

        return device_hash, device_data

    except Exception:
        logger.exception("Failed to generate device hash")
        raise


def check_device_hash(user):
    try:
        matched = False

        device_hash, device_data = generate_device_hash()

        user_id = user.user_id if hasattr(user, "user_id") else user

        print(user_id, flush=True)

        pattern = f"device_hash:{user_id}:*"
        print("Redis key pattern:", pattern, flush=True)
        print(redis_.connection_pool.connection_kwargs["db"], flush=True)
        print(redis_.connection_pool.connection_kwargs, flush=True)

        keys = redis_.keys()

        print(keys, flush=True)
        keys = redis_.keys(pattern)

        print("Generated hash:", device_hash)
        print("Redis keys:", keys)

        for key in keys:
            print("Checking key:", key, flush=True)
            saved_hash = key.split(":")[-1]
            
            if saved_hash == device_hash:
                matched = True
                print("Hash matched!")
                return True
            
        print(user.email, flush=True)

        if not matched:
            print("Device hash mismatch. Sending verification email.", flush=True)
            try:
                send_emails(
                    user.email,
                    "Unrecognized device detected",
                    "Please change your password if this wasn't you."
                )
            except Exception:
                logger.exception("Failed to send verification email")
        return {
            "message": "Unrecognized device. Verification email sent."
        }, 403 

    except Exception:
        logger.exception("Device hash check failed")
        return False
    

def save_device_hash(new_user):
    try:
        device_hash, device_data = generate_device_hash()

        redis_key = f"device_hash:{new_user.user_id}:{device_hash}"
        
        print("Saving device hash in Redis with key:", redis_key, flush=True)

        try:
            redis_.set(redis_key, 1)
        except Exception:
            logger.exception("Failed to save device hash in Redis")

        signin_data = SignInAttempts(
                        user_id=new_user.user_id,
                        created_at=datetime.datetime.utcnow(),
                        device_mac=device_data["device_uuid"],
                        device_name=device_data["device_model"],
                        device_os=device_data["device_os"],
                        estimated_location = get_estimated_location(),
                    )

        db.session.add(signin_data)
        db.session.flush()

        new_user.last_seen_id = signin_data.id
        new_user.device_hash = device_hash

        db.session.commit()

        logger.info(
            "Device saved successfully for user_id={}",
            new_user.user_id
        )

        return True

    except Exception:
        db.session.rollback()
        logger.exception(
            "Failed to save device for user_id={}",
            getattr(new_user, "user_id", None)
        )
        return False

    
def get_location():
    # Get IP address
    if request.headers.get('X-Forwarded-For'):
        ip_address = request.headers.get('X-Forwarded-For').split(',')[0]
    else:
        ip_address = request.remote_addr

    # Lookup location (path to your local MaxMind database)
    try:
        with geoip2.database.Reader('GeoLite2-City.mmdb') as reader:
            response = reader.city(ip_address)
            city = response.city.name
            country = response.country.name
            return {'ip': ip_address, 'city': city, 'country': country}
    except Exception:
        return {'ip': ip_address, 'error': 'Location not found'}

        
def get_estimated_location():
    try:

        data = get_location()

        print("Location data:", data, flush=True)

        return {
            "ip": data.get("ip"),
            "city": data.get("city"),
            "country": data.get("country"),
        }

    except requests.RequestException as e:
        logger.exception(
            "Failed to fetch estimated location: %s",
            e
        )
        return {}

    except Exception as e:
        logger.exception(
            "Unexpected error while fetching estimated location: %s",
            e
        )
        return {}



def send_emails(to_email, subject, body):
    try:

        sender_email = "shyamgundetin@gmail.com"
        sender_password = "qfdgagqxljuoascx"

        message = MIMEMultipart()

        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)

    except Exception as e:    
        logger.exception("Failed to send email: %s", e)

